import sys
import os

# プロジェクトのルートディレクトリ(coreパッケージがある場所)をパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from .node import CameraNode
except ImportError:
    from camera_node.node import CameraNode

def main():
    node = CameraNode()
    node.run()

if __name__ == "__main__":
    main()