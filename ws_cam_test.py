import cv2, asyncio, websockets, base64, json, time

WS_URL = "ws://127.0.0.1:8001/ws/user123/exam456"

async def run():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Khong mo duoc camera")
        return

    async with websockets.connect(WS_URL, max_size=20_000_000) as ws:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            # Nén ảnh gửi YOLO service
            _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

            t0 = time.perf_counter()
            await ws.send(json.dumps({"image": b64}))
            resp_text = await ws.recv()
            dt = (time.perf_counter() - t0) * 1000

            # Parse response
            try:
                resp = json.loads(resp_text)
            except:
                resp = {}

            violations = resp.get("violations", [])
            warning_count = resp.get("warning_count", 0)
            is_blocked = resp.get("is_blocked", False)

            # Overlay text lên frame
            status = f"Latency: {dt:.1f} ms | Warnings: {warning_count} | Blocked: {is_blocked}"
            cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            y = 55
            if violations:
                for v in violations[:4]:
                    msg = f"{v.get('action')} ({v.get('confidence',0):.2f})"
                    cv2.putText(frame, msg, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    y += 28
                print("VIOLATIONS:", [v.get("action") for v in violations])

            cv2.imshow("YOLO Realtime Test - press q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()

asyncio.run(run())
