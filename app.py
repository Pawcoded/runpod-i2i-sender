import os
import json
import time
from datetime import datetime
from pathlib import Path

import runpod
from flask import Flask, Response, render_template, request

app = Flask(__name__)

# RunPod settings
api_key = os.getenv("RUNPOD_API_KEY")
endpoint_id = os.getenv("ENDPOINT_ID")

# Directory for logs and last response
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if api_key:
    runpod.api_key = api_key


def save_log_and_response(log_lines, response_data=None):
    """Save log and latest response to output/ (overwrites previous files)."""
    with open(OUTPUT_DIR / "last_request.log", "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    if response_data is not None:
        with open(OUTPUT_DIR / "response.json", "w", encoding="utf-8") as f:
            json.dump(response_data, f, indent=4, ensure_ascii=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/send", methods=["POST"])
def send_request():
    """Send image request to RunPod and stream progress over SSE."""
    data = request.get_json(silent=True) or {}
    image_b64 = (data.get("image") or "").strip()

    if not image_b64:
        return {"error": "Image is missing"}, 400

    if not api_key or not endpoint_id:
        return {"error": "RUNPOD_API_KEY or ENDPOINT_ID is not set"}, 500

    def generate():
        log_lines = []
        response_data = None

        def log(message):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_lines.append(f"[{timestamp}] {message}")

        try:
            endpoint = runpod.Endpoint(endpoint_id)

            msg = f"Connecting to endpoint {endpoint_id}..."
            log(msg)
            yield f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"

            payload = {
                "image": image_b64,
                "image_name": data.get("image_name"),
            }

            img_size_kb = len(image_b64) * 3 / 4 / 1024
            msg = f"Sending image (~{img_size_kb:.0f} KB)..."
            log(msg)
            yield f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"

            run_request = endpoint.run(payload)
            job_id = run_request.job_id

            msg = f"Job submitted (ID: {job_id}). Waiting for completion..."
            log(msg)
            yield f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"

            # Status polling
            timeout = 1200
            start_time = time.time()
            last_status = None

            while time.time() - start_time < timeout:
                status = run_request.status()

                if status != last_status:
                    msg = f"Status: {status}"
                    log(msg)
                    yield f"data: {json.dumps({'type': 'status', 'message': msg})}\n\n"
                    last_status = status

                if status == "COMPLETED":
                    output = run_request.output()
                    response_data = output

                    if isinstance(output, dict) and "error" in output:
                        error_msg = output.get("error")
                        details = output.get("details", [])
                        msg = f"Worker error: {error_msg}"
                        if details:
                            msg += f" | Details: {details}"
                        log(msg)
                        yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
                        save_log_and_response(log_lines, response_data)
                        return

                    msg = "Job completed!"
                    log(msg)

                    # Try to extract image from response
                    result_image = extract_image(output)

                    event_data = {
                        "type": "complete",
                        "message": msg,
                        "output": output,
                    }
                    if result_image:
                        event_data["image"] = result_image

                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    save_log_and_response(log_lines, response_data)
                    return

                if status == "FAILED":
                    msg = "Job failed."
                    log(msg)
                    yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
                    save_log_and_response(log_lines)
                    return

                time.sleep(3)

            msg = f"Timeout: job was not completed within {timeout} seconds."
            log(msg)
            yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
            save_log_and_response(log_lines)

        except Exception as e:
            msg = f"Error: {str(e)}"
            log(msg)
            yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
            save_log_and_response(log_lines)

    return Response(generate(), mimetype="text/event-stream")


def extract_image(output):
    """Extract base64 image or URL from RunPod response.

    Worker runpod_comfyui_i2i_housemaid may return:
    {
        "prompt_id": "...",
        "images": [{"filename": "...", "type": "base64", "data": "..."}],
        "image": "<base64>"
    }
    """
    if isinstance(output, str):
        if output.startswith("http"):
            return {"type": "url", "data": output}
        if len(output) > 100 and " " not in output:
            return {"type": "base64", "data": output}

    if isinstance(output, dict):
        # Direct image field
        direct = output.get("image")
        if isinstance(direct, str):
            if direct.startswith("http"):
                return {"type": "url", "data": direct}
            if len(direct) > 100:
                return {"type": "base64", "data": direct}

        for key in ["images", "result", "output"]:
            val = output.get(key)
            if val is not None:
                if isinstance(val, list) and len(val) > 0:
                    val = val[0]

                if isinstance(val, dict):
                    # Support newer format with s3_url / base64
                    img_type = val.get("type")
                    img_data = val.get("data")

                    if img_type == "s3_url" and img_data:
                        return {"type": "url", "data": img_data}
                    if img_type == "base64" and img_data:
                        return {"type": "base64", "data": img_data}

                    val = val.get("data") or val.get("content", "")

                if isinstance(val, str):
                    if val.startswith("http"):
                        return {"type": "url", "data": val}
                    if len(val) > 100:
                        return {"type": "base64", "data": val}

    return None


if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    app.run(host="0.0.0.0", port=port, debug=False)
