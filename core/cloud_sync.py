import threading
import wx

EVT_SYNC_RESULT_ID = wx.NewIdRef()

def EVT_SYNC_RESULT(win, func):
    win.Connect(-1, -1, EVT_SYNC_RESULT_ID, func)

class SyncResultEvent(wx.PyEvent):
    def __init__(self, status, message=""):
        super().__init__()
        self.SetEventType(EVT_SYNC_RESULT_ID)
        self.status = status
        self.message = message

class MultiSourceSyncThread(threading.Thread):
    def __init__(self, parent, i18n, settings, sources):
        super().__init__(daemon=True)
        self.parent = parent
        self.i18n = i18n
        self.settings = settings
        self.sources = sources
        self.start()

    def run(self):
        wx.PostEvent(self.parent, SyncResultEvent("loading"))
        try:
            import time
            time.sleep(1.5)
            
            src_str = str(self.sources)
            msg = self.i18n.get("sync_msg_success")
            if "{sources}" in msg:
                msg = msg.replace("{sources}", src_str)
                
            wx.PostEvent(self.parent, SyncResultEvent("success", msg))
        except Exception as e:
            err_msg = self.i18n.get("sync_msg_exception")
            if "{error}" in err_msg:
                err_msg = err_msg.replace("{error}", str(e))
            wx.PostEvent(self.parent, SyncResultEvent("error", err_msg))