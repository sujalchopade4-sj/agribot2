import json, os, subprocess, time, streamlit as st

st.set_page_config(page_title="AgriBot Field Terminal", page_icon="🚜", layout="wide")

st.markdown("""
<style>
    .cell-5 { height: 68px; border-radius: 8px; display: flex; align-items: center; justify-content: center; position: relative; font-size: 24px; }
    .robot-cell { box-shadow: 0 0 14px #4ade80; border: 2px solid #4ade80 !important; }
    .base-station { border: 2px dashed #38bdf8 !important; }
    .coord-tag { position: absolute; bottom: 3px; right: 4px; font-size: 9px; opacity: 0.45; }
    .status-banner { border-left: 4px solid #4ade80; background: rgba(74, 222, 128, 0.08); padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; }
</style>
""", unsafe_allow_html=True)

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, "agribot_state.txt")
EXE_PATH = os.path.join(HERE, "agribot_core.exe" if os.name == "nt" else "agribot_core")
CPP_PATH = os.path.join(HERE, "agribot_core.cpp")

if not os.path.exists(EXE_PATH) or (os.path.exists(CPP_PATH) and os.path.getmtime(CPP_PATH) > os.path.getmtime(EXE_PATH)):
    subprocess.run(["g++", "-std=c++17", CPP_PATH, "-o", EXE_PATH], check=True)
    if os.name != "nt": os.chmod(EXE_PATH, 0o755)

def call_core(action, **kwargs):
    args = [EXE_PATH, STATE_FILE, action] + [f"{k}={v}" for k, v in kwargs.items()]
    return json.loads(subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip())

# FIX: only fetch a fresh "state" on the very first load of this session.
# Previously this ran unconditionally on every rerun (including the rerun
# that fires right after a button click), which overwrote the real message
# from that action ("Moved up to [...]", "Undo Stack is empty...", etc.)
# with the C++ program's default constructor message, since msg isn't
# persisted to the state file. Button clicks now own st.session_state.state
# from here on, so their messages actually stay visible.
if "state" not in st.session_state:
    st.session_state.state = call_core("state")

THEME = {
    "H": {"bg": "#064e3b", "border": "#10b981", "icon": "🌱"},
    "W": {"bg": "#78350f", "border": "#f59e0b", "icon": "🌾"},
    "D": {"bg": "#7f1d1d", "border": "#ef4444", "icon": "🥀"}
}
FOG = {"bg": "#182026", "border": "#334155", "icon": "🌫️"}

st.title("🛰️ AgriBot 5x5 Tactical Field Terminal")

with st.expander("⚡ AUTONOMOUS SWEEP & SPEED CONTROLLER", expanded=True):
    c1, c2 = st.columns([1.5, 1])
    speed = c1.slider("Step Delay (seconds)", 0.05, 1.0, 0.25, 0.05)
    if c2.button("🚀 Queue Full Lawnmower Sweep", use_container_width=True):
        cur_x, cur_y = st.session_state.state["x"], st.session_state.state["y"]
        for r in range(5):
            for c in (range(5) if r % 2 == 0 else range(4, -1, -1)):
                while cur_x < r: call_core("queue_add", type="move", dir="down"); cur_x += 1
                while cur_x > r: call_core("queue_add", type="move", dir="up"); cur_x -= 1
                while cur_y < c: call_core("queue_add", type="move", dir="right"); cur_y += 1
                while cur_y > c: call_core("queue_add", type="move", dir="left"); cur_y -= 1
                call_core("queue_add", type="inspect")
        st.session_state.state = call_core("state")
        st.rerun()

banner = st.empty()
col_map, col_ops = st.columns([1.5, 1], gap="large")

def render_matrix(holder, s):
    with holder.container():
        st.subheader("Field Matrix")
        for r in range(5):
            cols = st.columns(5)
            for c in range(5):
                is_bot = (s["x"] == r and s["y"] == c)
                is_base = (r == 0 and c == 0)
                m = THEME[s["grid"][r][c]] if s["discovered"][r][c] else FOG
                icon = "🤖" if is_bot else (m["icon"] if not is_base else "⚡")
                cls = f"cell-5 {'robot-cell' if is_bot else ('base-station' if is_base else '')}"
                cols[c].markdown(f'<div class="{cls}" style="background:{m["bg"]}; border:1px solid {m["border"]};"><span>{icon}</span><span class="coord-tag">{r},{c}</span></div>', unsafe_allow_html=True)

with col_map:
    matrix_ph = st.empty()
    render_matrix(matrix_ph, st.session_state.state)
    st.markdown("🤖 **Rover** | ⚡ **Solar Dock [0,0]** | 🌫️ **Fog** | 🌱 **Healthy** | 🌾 **Weed** | 🥀 **Blight**")

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if c2.button("⬆️ North", use_container_width=True): st.session_state.state = call_core("move", dir="up"); st.rerun()
    c4, c5, c6 = st.columns(3)
    if c4.button("⬅ West", use_container_width=True): st.session_state.state = call_core("move", dir="left"); st.rerun()
    if c5.button("⬇️ South", use_container_width=True): st.session_state.state = call_core("move", dir="down"); st.rerun()
    if c6.button("➡️ East", use_container_width=True): st.session_state.state = call_core("move", dir="right"); st.rerun()

    a1, a2, a3 = st.columns(3)
    if a1.button("🔬 Inspect (-1%)", use_container_width=True): st.session_state.state = call_core("inspect"); st.rerun()
    if a2.button("💦 Spray (-3%)", use_container_width=True): st.session_state.state = call_core("spray"); st.rerun()
    if a3.button("⚡ Recharge", use_container_width=True, disabled=not (st.session_state.state["x"] == 0 and st.session_state.state["y"] == 0)):
        st.session_state.state = call_core("recharge"); st.rerun()

    u1, u2, u3 = st.columns(3)
    if u1.button("⏪ Undo Stack", use_container_width=True): st.session_state.state = call_core("undo"); st.rerun()
    if u2.button("⏩ Redo Stack", use_container_width=True): st.session_state.state = call_core("redo"); st.rerun()
    if u3.button("🔄 Reset Field", use_container_width=True): st.session_state.state = call_core("reset"); st.rerun()

with col_ops:
    st.subheader("Diagnostics")
    batt = st.session_state.state["battery"]
    disc = sum(sum(1 for cell in row if cell) for row in st.session_state.state["discovered"])
    d1, d2, d3 = st.columns(3)
    d1.metric("Reserve Power", f"{batt}%")
    d2.metric("Grid Vector", f"[{st.session_state.state['x']}, {st.session_state.state['y']}]")
    d3.metric("Scouted", f"{disc}/25")
    st.progress(batt / 100)

    st.markdown("---")
    st.subheader("Mission Pipeline (`std::queue`)")
    s1, s2 = st.columns(2)
    q_act = s1.selectbox("Action", ["move", "spray", "inspect", "recharge"])
    q_dir = s2.selectbox("Direction", ["up", "down", "left", "right"]) if q_act == "move" else None

    b1, b2, b3 = st.columns(3)
    if b1.button("Push Queue", use_container_width=True):
        payload = {"type": q_act}
        if q_dir: payload["dir"] = q_dir
        st.session_state.state = call_core("queue_add", **payload)
        st.rerun()
    if b2.button("Step Queue", use_container_width=True):
        st.session_state.state = call_core("queue_next")
        st.rerun()
    if b3.button("▶️ Run Queue", use_container_width=True):
        while st.session_state.state["queue"]:
            st.session_state.state = call_core("queue_next")
            render_matrix(matrix_ph, st.session_state.state)
            banner.markdown(f'<div class="status-banner"><strong>TELEMETRY:</strong> {st.session_state.state.get("msg","Running...")}</div>', unsafe_allow_html=True)
            time.sleep(speed)
        st.rerun()

    # Active Pipeline Visualizer
    with st.expander("Active Pipeline Tasks (`FIFO Queue`)", expanded=True):
        if st.session_state.state["queue"]:
            for idx, q_cmd in enumerate(st.session_state.state["queue"][:10], 1):
                clean_name = q_cmd.replace(":", " ➔ ")
                st.code(f"QUEUE #{idx}: {clean_name}")
            if len(st.session_state.state["queue"]) > 10:
                st.caption(f"...and {len(st.session_state.state['queue']) - 10} more in queue.")
        else:
            st.caption("No instructions in pipeline.")

    tu, tr = st.tabs(["LIFO Undo Stack", "LIFO Redo Stack"])
    with tu:
        if st.session_state.state["undo"]:
            for it in reversed(st.session_state.state["undo"][-8:]):
                st.text(f"⮌ {it.split(':')[0]}")
        else:
            st.caption("Undo stack empty.")
    with tr:
        if st.session_state.state["redo"]:
            for it in reversed(st.session_state.state["redo"][-8:]):
                st.text(f"⮎ {it.split(':')[0]}")
        else:
            st.caption("Redo stack empty.")

banner.markdown(f'<div class="status-banner"><strong>TELEMETRY:</strong> {st.session_state.state.get("msg","Ready.")}</div>', unsafe_allow_html=True)
