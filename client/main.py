import tkinter as tk
from ui import MessengerUI

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 VERCEL MESSENGER")
    print("=" * 50)

    root = tk.Tk()
    app = MessengerUI(root)
    root.mainloop()