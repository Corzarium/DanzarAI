import subprocess, sys

def run(script):
    subprocess.run([sys.executable, script], check=True)

if __name__ == "__main__":
    run("poe2wiki.py")
    run("build_rag_index.py")
    # restart your rag_server if needed:
    subprocess.run(["pkill","-f","rag_server.py"])
    subprocess.Popen([sys.executable,"rag_server.py"])
