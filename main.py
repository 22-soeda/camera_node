import sys
import os

# プロジェクトのルートディレクトリ(coreパッケージがある場所)をパスに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from .node import CameraNode

def main():
    node = CameraNode()
    node.run()

if __name__ == "__main__":
    main()