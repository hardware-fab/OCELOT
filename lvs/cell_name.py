import sys

print("".join(ch if (ch.isalnum() or ch in "_$") else "_" for ch in sys.argv[1]))
