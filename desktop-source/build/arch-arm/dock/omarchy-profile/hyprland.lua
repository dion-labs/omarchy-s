-- Prepared Omarchy appearance subset; no provisioning, autostart or power policy.
-- The upstream source and license are preserved beside this file.
local profile = os.getenv("S9P_OMARCHY_PROFILE") or "/trial/profile"
dofile(profile .. "/upstream/looknfeel.lua")
hl.monitor({ output = "", mode = "1920x1080@30", position = "auto", scale = 1 })
hl.config({
  input = { kb_layout = "it" },
  animations = { enabled = false },
  decoration = { blur = { enabled = false }, shadow = { enabled = false } },
})

-- Small native desktop entry points; no upstream service/provisioning assumptions.
hl.bind("SUPER + SPACE", hl.dsp.exec_cmd("python3 /trial/shell-menu.py"), { description = "Desktop launcher" })
hl.bind("SUPER + E", hl.dsp.exec_cmd("nautilus --new-window /trial/home"), { description = "Files" })
hl.bind("SUPER + N", hl.dsp.exec_cmd("env GSK_RENDERER=cairo gnome-text-editor --standalone"), { description = "New document" })
hl.bind("SUPER + F", hl.dsp.window.fullscreen({ mode = "fullscreen" }), { description = "Full screen" })
hl.bind("SUPER + Q", hl.dsp.window.close(), { description = "Close window" })
hl.bind("SUPER + T", hl.dsp.window.float({ action = "toggle" }), { description = "Float or tile window" })
for key, direction in pairs({ LEFT = "l", RIGHT = "r", UP = "u", DOWN = "d" }) do
  hl.bind("SUPER + " .. key, hl.dsp.focus({ direction = direction }), { description = "Focus " .. direction })
end

hl.bind("SUPER + SHIFT + SPACE", hl.dsp.exec_cmd("python3 /trial/launchpad.py"), { description = "Desktop help and fallback launcher" })

-- Upstream Omarchy workspace and tiling actions, using physical number-row keys.
for workspace = 1, 10 do
  local key = "code:" .. tostring(workspace + 9)
  hl.bind("SUPER + " .. key, hl.dsp.focus({ workspace = tostring(workspace) }), { description = "Workspace " .. workspace })
  hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.move({ workspace = tostring(workspace) }), { description = "Move to workspace " .. workspace })
end
for key, direction in pairs({ LEFT = "l", RIGHT = "r", UP = "u", DOWN = "d" }) do
  hl.bind("SUPER + SHIFT + " .. key, hl.dsp.window.swap({ direction = direction }), { description = "Swap " .. direction })
end
hl.bind("SUPER + J", hl.dsp.layout("togglesplit"), { description = "Toggle split" })
hl.bind("ALT + TAB", hl.dsp.window.cycle_next(), { description = "Next window" })
hl.bind("ALT + SHIFT + TAB", hl.dsp.window.cycle_next({ next = false }), { description = "Previous window" })
hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true, description = "Move window" })
hl.bind("SUPER + mouse:273", hl.dsp.window.resize(), { mouse = true, description = "Resize window" })

local theme = os.getenv("HOME") .. "/.config/omarchy-s/theme.lua"
local file = io.open(theme, "r")
if file then file:close(); dofile(theme) end

hl.bind("SUPER + V", hl.dsp.exec_cmd("quickshell ipc -p /trial/omarchy-shell/shell call shell toggle omarchy.clipboard '{}'"), { description = "Clipboard history" })

hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd("python3 /trial/screenshot.py"), { description = "Save screenshot" })

hl.bind("SUPER + RETURN", hl.dsp.exec_cmd("python3 /trial/app-launch.py terminal"), { description = "Terminal" })

hl.bind("SUPER + CTRL + W", hl.dsp.exec_cmd("quickshell ipc -p /trial/omarchy-shell/shell call shell toggle omarchy.network '{}'"), { description = "Wi-Fi" })

hl.bind("SUPER + CTRL + B", hl.dsp.exec_cmd("quickshell ipc -p /trial/omarchy-shell/shell call shell toggle omarchy.bluetooth '{}'"), { description = "Bluetooth" })
