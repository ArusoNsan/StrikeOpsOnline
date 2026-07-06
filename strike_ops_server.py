#!/usr/bin/env python3
"""
STRIKE OPS リレーサーバー (ホスト権威型のための純中継)
- ゲームロジックは一切持たない: ルーム管理 + メッセージ転送のみ
- ローカル:  python strike_ops_server.py  (port 8732)
- Render等: PORT環境変数を読む。requirements.txt に websockets が必要
プロトコル (JSONテキストフレーム):
  c→s {"t":"hello","room":"ABCD","name":"..","team":"CT"|"T"|"auto"}
  s→c {"t":"welcome","id":n,"host":true/false,"roster":[...]}
  s→全員 {"t":"roster","roster":[{"id","name","team","host"}...]}
  ゲスト→s {"t":"in",...}   → ホストにのみ転送
  ホスト→s {"t":"snap"/"start"/...} → ホスト以外の全員に転送
  s→全員 {"t":"hostleft"} ホスト切断時 (ルーム解散)
"""
import asyncio, json, os, signal
from websockets.asyncio.server import serve

rooms = {}  # code -> {"clients": {id: ws}, "meta": {id: {...}}, "host": id, "next": int}

def roster_of(room):
    return [{"id": i, "name": m.get("name","?"), "team": m.get("team","auto"),
             "host": i == room["host"]} for i, m in room["meta"].items()]

async def send(ws, obj):
    try:
        await ws.send(json.dumps(obj))
    except Exception:
        pass

async def broadcast(room, obj, exclude=None):
    msg = json.dumps(obj)
    for i, ws in list(room["clients"].items()):
        if i == exclude:
            continue
        try:
            await ws.send(msg)
        except Exception:
            pass

async def handler(ws):
    room = None
    cid = None
    code = None
    try:
        raw = await asyncio.wait_for(ws.recv(), timeout=15)
        hello = json.loads(raw)
        if hello.get("t") != "hello":
            await ws.close()
            return
        code = str(hello.get("room", "MAIN"))[:12].upper()
        room = rooms.get(code)
        if room is None:
            room = {"clients": {}, "meta": {}, "host": None, "next": 1}
            rooms[code] = room
        if len(room["clients"]) >= 10:
            await send(ws, {"t": "error", "msg": "room full"})
            await ws.close()
            return
        cid = room["next"]; room["next"] += 1
        room["clients"][cid] = ws
        room["meta"][cid] = {"name": str(hello.get("name", "player"))[:16],
                             "team": hello.get("team", "auto")}
        if room["host"] is None:
            room["host"] = cid
        await send(ws, {"t": "welcome", "id": cid, "host": room["host"] == cid,
                        "roster": roster_of(room)})
        await broadcast(room, {"t": "roster", "roster": roster_of(room)}, exclude=cid)
        print(f"[{code}] join id={cid} name={room['meta'][cid]['name']} "
              f"({len(room['clients'])} in room)")

        async for raw in ws:
            try:
                # 転送方向は"t"で決める。中身は解釈しない(高頻度なのでパース最小化)
                head = raw[:24]
                if '"in"' in head:      # ゲスト入力 → ホストへ
                    hws = room["clients"].get(room["host"])
                    if hws is not None and cid != room["host"]:
                        await hws.send(raw)
                elif cid == room["host"]:  # ホスト発 (snap/start/ev等) → 他全員へ
                    for i, w in list(room["clients"].items()):
                        if i != cid:
                            try:
                                await w.send(raw)
                            except Exception:
                                pass
                else:
                    # ゲスト発のその他 (チャット等将来用) → ホストへ
                    hws = room["clients"].get(room["host"])
                    if hws is not None:
                        await hws.send(raw)
            except Exception:
                pass
    except Exception:
        pass
    finally:
        if room is not None and cid is not None:
            room["clients"].pop(cid, None)
            room["meta"].pop(cid, None)
            print(f"[{code}] leave id={cid} ({len(room['clients'])} in room)")
            if cid == room["host"]:
                await broadcast(room, {"t": "hostleft"})
                for w in list(room["clients"].values()):
                    try:
                        await w.close()
                    except Exception:
                        pass
                rooms.pop(code, None)
            else:
                await broadcast(room, {"t": "roster", "roster": roster_of(room)})
            if not room["clients"]:
                rooms.pop(code, None)

async def main():
    port = int(os.environ.get("PORT", "8732"))
    async with serve(handler, "", port):
        print(f"STRIKE OPS relay listening on :{port}")
        await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
