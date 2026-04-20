import threading
import queue
import shlex

class TerminalHandler:
    """ターミナルからの標準入力を別スレッドで処理するクラス"""
    def __init__(self, cmd_queue: queue.Queue):
        self.cmd_queue = cmd_queue
        # daemon=True にすることで、メインプログラム終了時に自動でスレッドも終了する
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def _run(self):
        print("\n--- Terminal Command Help ---")
        print("  connect [driver] [port]")
        print("  disconnect")
        print("  set_exposure [us]")
        print("  get_exposure")
        print("  set_target_brightness [0-255]")
        print("  get_target_brightness")
        print("  adjust_exposure [max_iterations] [tolerance] [sleep_s]")
        print("  set_gain [value]")
        print("  set_fps [fps]")
        print("  set_mode [continuous|trigger]")
        print("  capture [save_dir]")
        print("-----------------------------\n")
        
        while True:
            try:
                line = input().strip()
                if not line: continue
                
                parts = shlex.split(line)
                action = parts[0].lower()
                cmd = {"action": action}
                
                if action == "connect":
                    cmd["driver"] = parts[1] if len(parts) > 1 else "dummy"
                    cmd["port"] = parts[2] if len(parts) > 2 else "0"
                elif action == "set_target_brightness":
                    if len(parts) > 1:
                        cmd["value"] = float(parts[1])
                    else:
                        print("[Terminal] Missing value. Format: set_target_brightness [0-255]")
                        continue
                elif action == "get_target_brightness":
                    pass
                elif action == "get_exposure":
                    cmd["terminal"] = True
                elif action == "adjust_exposure":
                    if len(parts) > 1:
                        cmd["max_iterations"] = int(parts[1])
                    if len(parts) > 2:
                        cmd["tolerance"] = float(parts[2])
                    if len(parts) > 3:
                        cmd["sleep_s"] = float(parts[3])
                elif action in ["set_exposure", "set_gain", "set_fps"]:
                    if len(parts) > 1: cmd["value"] = float(parts[1])
                    else:
                        print(f"[Terminal] Missing value. Format: {action} [value]")
                        continue
                elif action == "set_mode":
                    if len(parts) > 1: cmd["value"] = parts[1]
                    else:
                        print(f"[Terminal] Missing value. Format: set_mode [continuous|trigger]")
                        continue
                elif action == "capture":
                    if len(parts) > 1:
                        cmd["save_dir"] = parts[1]
                        
                # キューにコマンドを積む
                self.cmd_queue.put(cmd)
                
            except EOFError:
                break
            except Exception as e:
                print(f"[Terminal] Input error: {e}")