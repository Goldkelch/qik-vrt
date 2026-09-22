#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Isolated, hash-checked Linux x86_64 Rust/GHDL provisioning; C90 uses the host CC."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
def run(args,env):return subprocess.check_output(list(map(str,args)),env=env,stderr=subprocess.STDOUT,timeout=240).decode()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prefix",type=Path,required=True)
    p.add_argument("--install",action="store_true")
    a=p.parse_args();prefix=a.prefix.expanduser().absolute();lock=json.loads((ROOT/"toolchains.lock.json").read_text())
    if (platform.system(),platform.machine())!=("Linux","x86_64"):raise SystemExit("This provisioner targets Linux x86_64; provide platform CC/Rust/GHDL explicitly on other hosts.")
    for parent in [prefix,*prefix.parents]:
        if parent.is_symlink():raise SystemExit("Symlink cache prefix rejected")
    if a.install:prefix.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,RUSTUP_HOME=str(prefix/"rustup"),CARGO_HOME=str(prefix/"cargo"))
    ghdl=prefix/"ghdl/install/usr/bin/ghdl-mcode"
    env["LD_LIBRARY_PATH"]=str(prefix/"ghdl/install/usr/lib/x86_64-linux-gnu")
    env["GHDL_PREFIX"]=str(prefix/"ghdl/install/usr/lib/ghdl/mcode")
    cache=prefix/"downloads"
    def download(url,filename,digest):
        path=cache/filename
        if path.exists():
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError("Cached artifact mismatch: "+filename)
            return path
        if not a.install:raise ValueError("Missing verified cache: "+filename)
        cache.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache,delete=False) as f:
            temporary=Path(f.name)
            with urllib.request.urlopen(url,timeout=40) as source:shutil.copyfileobj(source,f)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=digest:raise ValueError("Downloaded artifact mismatch: "+filename)
        os.link(temporary,path);temporary.unlink();return path
    rustup=prefix/"cargo/bin/rustup"
    if a.install and not rustup.exists():
        installer=lock["rust"]["installer"];path=download(installer["url"],"rustup-init-"+installer["version"],installer["sha256"])
        path.chmod(0o700)
        print(run([path,"-y","--no-modify-path","--profile","minimal","--default-toolchain",lock["rust"]["version"]],env),flush=True)
    elif a.install:
        print(run([rustup,"toolchain","install",lock["rust"]["version"],"--profile","minimal"],env),flush=True)
    # Verify every package payload byte, including executable bits and symlink targets.
    for package in lock["ghdl"]["packages"]:
        filename=Path(package["Filename"]).name
        path=download("https://deb.debian.org/debian/"+package["Filename"],filename,package["SHA256"])
        install=prefix/"ghdl/install"
        if a.install:
            install.mkdir(parents=True,exist_ok=True)
            print("EXTRACT "+package["Package"],flush=True)
            run(["dpkg-deb","-x",path,install],env)
        process=subprocess.Popen(["dpkg-deb","--fsys-tarfile",str(path)],stdout=subprocess.PIPE)
        with tarfile.open(fileobj=process.stdout,mode="r|*") as archive:
            for member in archive:
                relative=Path(member.name)
                if relative.is_absolute() or ".." in relative.parts:raise ValueError("Unsafe package path")
                target=install/relative
                if member.isfile():
                    data=archive.extractfile(member).read()
                    if not target.is_file() or target.is_symlink() or target.read_bytes()!=data:raise ValueError("Extracted bytes differ: "+str(relative))
                    if member.mode&0o111 and target.stat().st_mode&0o111!=member.mode&0o111:raise ValueError("Executable mode differs")
                elif member.issym():
                    if not target.is_symlink() or os.readlink(target)!=member.linkname:raise ValueError("Extracted link differs")
        if process.wait()!=0:raise ValueError("Package verification failed")
    rust=run([prefix/"cargo/bin/rustc","+"+lock["rust"]["version"],"--version"],env).strip()
    hardware=run([ghdl,"--version"],env).splitlines()[0]
    if not rust.startswith("rustc "+lock["rust"]["version"]+" ") or "GHDL 2.0.0" not in hardware:raise ValueError("Tool version mismatch")
    cc=run([os.environ.get("CC","cc"),"--version"],env).splitlines()[0]
    host_tools={name:run([name,"--version"],env).splitlines()[0] for name in ("git","make","ar","dpkg-deb")}
    exports={"RUSTUP_HOME":env["RUSTUP_HOME"],"CARGO_HOME":env["CARGO_HOME"],"GHDL_PREFIX":env["GHDL_PREFIX"],
        "LD_LIBRARY_PATH":env["LD_LIBRARY_PATH"],"QIKVRT_CARGO":str(prefix/"cargo/bin/cargo"),"QIKVRT_GHDL":str(ghdl)}
    receipt={"state":"PASS","rust":rust,"ghdl":hardware,"cc":cc,"host_tools":host_tools,"lock_sha256":hashlib.sha256((ROOT/"toolchains.lock.json").read_bytes()).hexdigest()}
    if a.install:
        (prefix/"target-env.sh").write_text("\n".join("export "+key+"="+shlex.quote(value) for key,value in exports.items())+"\n")
        (prefix/"target-toolchain-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
