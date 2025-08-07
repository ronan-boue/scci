from fastapi import FastAPI, Form, Request, status
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from _version import __version__

PORT = 80

# ------------------------------------------------------------------------------
# Start SyncIoT thread
# ------------------------------------------------------------------------------
if True:
    from synciot import SyncIoT

    synciot = SyncIoT()
    if not synciot.init():
        print("Failed to initialize SyncIoT")
        exit(1)

    synciot.start_thread()
    print("SyncIoT thread started successfully.")
else:
    PORT = 8081
    print("SyncIoT thread not started. Set the condition to True to start it.")

# ------------------------------------------------------------------------------
# FastAPI application
# ------------------------------------------------------------------------------

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    event_count = 0
    event_time = "?"
    try:
        event_count = synciot.get_event_count()  # Assuming SyncIoT has a get_event_count method
    except Exception as e:
        print(f"Error getting event count: {e}")
        event_count = 0

    try:
        event_time = synciot.get_last_event_time()  # Assuming SyncIoT has a get_last_event_time method
    except Exception as e:
        print(f"Error getting last event time: {e}")
        event_time = "?"

    print(f"Request for index page received event_count={event_count} event_time={event_time}")
    return templates.TemplateResponse('index.html', {"request": request, "event_count": event_count, "event_time": event_time, "synciot_version": __version__})

@app.get('/favicon.ico')
async def favicon():
    file_name = 'favicon.ico'
    file_path = './static/' + file_name
    return FileResponse(path=file_path, headers={'mimetype': 'image/vnd.microsoft.icon'})

# ------------------------------------------------------------------------------
# Start FastAPI server
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        print("Starting FastAPI server. Press Ctrl+C to exit.")
        uvicorn.run('main:app', host='0.0.0.0', port=PORT)
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received. Shutting down...")
        # Clean up resources
        synciot.stop_thread()  # Assuming SyncIoT has a stop_thread method
        print("SyncIoT thread stopped.")
    finally:
        print("Application shutdown complete.")
