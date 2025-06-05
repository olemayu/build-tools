#!/usr/bin/python3
import subprocess, sys, os, glob, re


def error(message:str):
	print(message)
	exit(1)


build_file = os.path.realpath(__file__)
make_file = os.path.join(os.path.dirname(build_file), "Makefile")
configs = glob.glob("configs/*.mk")

if (not os.path.exists(".clangd") or
	min([os.stat(f) for f in configs + [make_file]]).st_mtime_ns > os.stat(".clangd").st_mtime_ns or
	os.stat(build_file).st_mtime_ns > os.stat(".clangd").st_mtime_ns):
	subprocess.run([ 
		"make",
		"-f", f"{make_file}",
		"flags",
		"make_target=linux", 
		"make_config=development",
		"make_build=default"
	], check=True)
	subprocess.run([ 
		"make",
		"-f", f"{make_file}",
		"flags",
		"make_target=win32", 
		"make_config=development",
		"make_build=default"
	], check=True)

	with open(".clangd", "w") as f:
		with open("linux.development.cflags", "r") as s:
			linux_cflags = re.findall(r'"[^"]*"|\S+', s.read())
		with open("win32.development.cflags", "r") as s:
			win32_cflags = re.findall(r'"[^"]*"|\S+', s.read())
		
		f.write(
			 "CompileFlags:\n"
			 "  Compiler: clang\n"
			 "  Add: [\n"
			 "    -xc,\n"
			 "    -ferror-limit=80,\n"
			 "    -DNRG_IDE=true,\n"
			f"    -I{os.getcwd()}/include,\n"
			f"    -I{os.getcwd()}/source,\n"
			f"    {",\n    ".join(f'"{f.replace('"', '\\"')}"' for f in linux_cflags)}\n"
			 "  ]\n"
			 "---\n"
			 "If:\n"
			 '  PathMatch: ".*/.*.win32.c"\n'
			 "CompileFlags:\n"
			 "  Compiler: x86_64-w64-mingw32.static-clang\n"
			 "  Add: [\n"
			f"    {",\n    ".join(f'"{f.replace('"', '\\"')}"' for f in linux_cflags)}\n"
			 "  ]\n")


if len(sys.argv) <= 1:
	error("no args")

options = []

for arg in sys.argv[1:]:
	options.extend(list(arg))

args = [ "make" ]
trace = False

if "j" in options:
	args.extend([ f"-j{os.cpu_count()}" ])

if "t" in options:
	trace = True
	args.extend([ "--trace" ])

if "c" in options:
	args.extend([ "clean" ])
elif "C" in options:
	args.extend([ "clean-all" ])
elif "x" in options:
	args.append("execute")
else:
	args.append("default")

if "l" in options:
	make_target = "linux"
elif "w" in options:
	make_target = "win32"
else:
	error("no platform provided")

if "r" in options:
	make_config = "release"
else:
	make_config = "development"

args.extend([
	"-f", f"{make_file}",
	f"make_target={make_target}", 
	f"make_config={make_config}",
	 "make_build=default",
	 "--no-print-directory"
])

if trace:
	print(args)
exit(subprocess.run(args).returncode)