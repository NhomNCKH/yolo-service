import asyncio, base64, json, time
import websockets

WS_URL = "ws://localhost:8001/ws/user123/exam456"
IMG_PATH = "test.jpg"      # đổi thành ảnh của bạn
TOTAL_FRAMES = 60          # số frame test
INTERVAL_SEC = 0.1         # 10 fps

async def main():
    with open(IMG_PATH, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    latencies = []
    async with websockets.connect(WS_URL, max_size=20_000_000) as ws:
        for i in range(TOTAL_FRAMES):
            payload = {"image": img_b64}
            t0 = time.perf_counter()
            await ws.send(json.dumps(payload))
            resp = await ws.recv()
            dt = (time.perf_counter() - t0) * 1000
            latencies.append(dt)
            print(f"frame={i+1:03d} latency_ms={dt:.1f} resp_len={len(resp)}")
            await asyncio.sleep(INTERVAL_SEC)

    avg = sum(latencies)/len(latencies)
    p95 = sorted(latencies)[int(len(latencies)*0.95)-1]
    print(f"\nAVG={avg:.1f}ms P95={p95:.1f}ms FPS_sent={1/INTERVAL_SEC:.1f}")

asyncio.run(main())
