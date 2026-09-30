"""
فحص إمكانية الوصول: يشغّل البرنامج ويقرأ كل نافذة عبر واجهة UI Automation
(نفس الواجهة التي يعتمد عليها قارئ الشاشة NVDA)، ويطبع ما سيُنطق لكل عنصر.
العناصر القابلة للتركيز بدون اسم تُعلَّم بـ "!! بدون اسم".

التشغيل:  python tests/a11y_audit.py
"""
import os
import subprocess
import sys
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERACTIVE = {"Edit", "ComboBox", "Button", "CheckBox", "List", "DataGrid", "Table", "Spinner",
               "Slider", "Tab", "TabItem", "RadioButton", "Document", "ProgressBar", "ListItem", "DataItem"}

problems = []


def dump(win, title):
    print(f"\n===== {title}: «{win.window_text()}»")
    for el in win.descendants():
        info = el.element_info
        ctype = info.control_type
        if ctype not in INTERACTIVE or ctype in ("ListItem", "DataItem"):
            continue
        name = (info.name or "").strip()
        focusable = el.is_keyboard_focusable() if hasattr(el, "is_keyboard_focusable") else True
        flag = ""
        # Spinner = أسهم الزيادة والنقصان الملحقة بحقل الأرقام: لا يقف عليها Tab، والحقل نفسه له اسم
        if not name and focusable and ctype not in ("Tab", "Spinner"):
            flag = "   !! بدون اسم"
            problems.append(f"{title} / {ctype} / id={info.automation_id}")
        # خانات الاختيار تُبلَّغ أحياناً كغير ظاهرة عبر UIA رغم أنها ظاهرة، فلا نخفيها
        if not el.is_visible() and ctype != "CheckBox":
            continue
        print(f"  {ctype:<12} «{name}»{flag}")


def wait_window(pid, exclude=(), timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        for w in Desktop(backend="uia").windows(process=pid):
            if w.handle not in exclude and w.is_visible():
                return w
        time.sleep(0.3)
    return None


def open_and_dump(pid, main, menu_path, title, tabs=0, close="{ESC}"):
    # فتح النافذة من القائمة بالأرقام (مثل "#2->#0") عبر رسائل ويندوز، بدون الاعتماد على لوحة المفاتيح
    from pywinauto import Application
    Application(backend="win32").connect(process=pid).top_window().menu_select(menu_path)
    time.sleep(2)
    dlg = None
    for w in Desktop(backend="uia").windows(process=pid):
        if w.handle != main.handle and w.is_visible():
            dlg = w
    if dlg is None:
        # النوافذ المشروطة (modal) تظهر كأبناء للنافذة الرئيسية
        kids = [c for c in main.children() if c.element_info.control_type == "Window"]
        dlg = kids[0] if kids else None
    if dlg is None:
        print(f"\n===== {title}: لم تفتح النافذة")
        return
    dump(dlg, title)
    for i in range(tabs):
        send_keys("^{TAB}")
        time.sleep(0.6)
        dump(dlg, f"{title} (تبويب {i + 2})")
    send_keys(close)
    time.sleep(1)


def main():
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "main.py")], cwd=ROOT)
    try:
        main_win = wait_window(proc.pid)
        time.sleep(2)
        dump(main_win, "النافذة الرئيسية")
        main_win.set_focus(); send_keys("^{TAB}"); time.sleep(0.8)
        dump(main_win, "النافذة الرئيسية - البحث الشامل")
        send_keys("^{TAB}"); time.sleep(0.5)

        # أرقام القوائم: 1=عرض، 2=أدوات، 3=مساعدة (الفواصل تُحسب ضمن الترقيم)
        open_and_dump(proc.pid, main_win, "#2->#0", "الإعدادات", tabs=4)
        open_and_dump(proc.pid, main_win, "#2->#3", "القاموس المخصص")
        open_and_dump(proc.pid, main_win, "#1->#7", "السجل")
        open_and_dump(proc.pid, main_win, "#3->#0", "اختصارات لوحة المفاتيح")
        open_and_dump(proc.pid, main_win, "#3->#1", "حول البرنامج")
        open_and_dump(proc.pid, main_win, "#2->#2", "إدارة النماذج", close="%{F4}")
    finally:
        proc.kill()

    print("\n\n===== ملخص: عناصر بدون اسم =====")
    for p in problems:
        print("  ", p)
    print(f"العدد: {len(problems)}")


if __name__ == "__main__":
    main()
