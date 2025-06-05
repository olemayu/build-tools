#!/usr/bin/python3

import subprocess, os, sys
import urllib.request
from io import StringIO
import hashlib

LLVM_VERSION  = 21
MXE_DIRECTORY = "/mxe"
MXE_PREFIX    = "x86_64-w64-mingw32"

APT_PACKAGES = [
	"autoconf",               "automake",               "autopoint",           "bash",
	"bison",                  "bzip2",                  "flex",                "g++",
	"g++-multilib",           "gettext",                "git",                 "gperf",
	"intltool",               "libc6-dev-i386",         "libclang-dev",        "libgdk-pixbuf2.0-dev",
	"libltdl-dev",            "libgl-dev",              "libpcre2-dev",        "libssl-dev",
	"libtool-bin",            "libxml-parser-perl",     "lzip",                "make",
	"openssl",                "p7zip-full",             "patch",               "perl",
	"python3",                "python3-mako",           "python3-packaging",   "python3-pkg-resources",
	"python3-setuptools",     "python-is-python3",      "ruby",                "sed",
	"sqlite3",                "unzip",                  "wget",                "xz-utils",
	f"clang-{LLVM_VERSION}", f"clangd-{LLVM_VERSION}", f"lld-{LLVM_VERSION}",
]

MXE_PACKAGES = [
	"cc", "sdl3", "jemalloc", "cpptrace"
]

YES_ALL = False


def error(message:str):
	print(message)
	exit(1)


class open_and_write_on_change:
	@staticmethod
	def get_hash(content):
		return hashlib.sha256(content.encode("utf-8")).hexdigest()

	def __init__(self, desc):
		self.desc = desc
		self.buf = StringIO()
		self.hash = None

		if os.path.exists(desc):
			with open(desc, "r") as f:
				self.hash = self.get_hash(f.read())

	def __enter__(self):
		return self.buf

	def __exit__(self, exception, _0, _1):
		if not exception:
			content = self.buf.getvalue()
			hash = self.get_hash(content)
			
			if hash != self.hash:
				with open(self.desc, "w") as f:
					f.write(content)


def underline(v):
	return f"\033[4m{v}\033[0m"


def prompt_to_run()->bool:
	global YES_ALL

	if not YES_ALL:
		while True:
			response = input(f"{underline('Y')}es / {underline('N')}o / {underline('A')}ll / {underline('S')}kip: ").strip().lower()
			if response in ("y", "yes"):
				break
			elif response in ("a", "all"):
				YES_ALL = True
				break
			elif response in ("s", "skip"):
				return False
			elif response in ("n", "no"):
				print("Abort")
				sys.exit(1)
	
	return True


def prompt_process(args: list[str])->bool:
	print(f"Run: \033[34m{' '.join(args)}\033[0m")
	if prompt_to_run():
		subprocess.run(args, check=True)
		return True
	
	return False


def prompt_process_shell(args:str):
	print(f"Run: \033[34m{args}\033[0m")
	if prompt_to_run():
		subprocess.run(args, shell=True, check=True)
		return True
	
	return False


def process_stdout(args:str):
	result = subprocess.run(args, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

	return result.stdout.decode('utf-8').strip()


def install_llvm_repository(llvm_version:str):
	# Reference: http://apt.llvm.org/llvm.sh
	list_path = f"/etc/apt/sources.list.d/spectre-llvm-clang{llvm_version}.list"

	if not os.path.exists("/etc/apt/trusted.gpg.d/apt.llvm.org.asc"):
		if not prompt_process_shell("sudo wget -qO- https://apt.llvm.org/llvm-snapshot.gpg.key | tee /etc/apt/trusted.gpg.d/apt.llvm.org.asc"):
			error(f"@TODO: error message")

	if not os.path.exists(list_path):
		distro = process_stdout('lsb_release -is')
		codename = process_stdout('lsb_release -cs')
		base_url = "http://apt.llvm.org"
		repo_url = f"{base_url}/{codename}/"
		repo_entry = f"deb {base_url}/{codename} llvm-toolchain-{codename}{llvm_version} main"

		try:
			req = urllib.request.Request(repo_url, method='HEAD')
			with urllib.request.urlopen(req):
				pass
		except:
			error(f"Distro {underline(distro)} with codename {underline(codename)} is not supported.")

		if (not prompt_process_shell(f"echo '{repo_entry}' | sudo tee {list_path}") or
			not prompt_process_shell("sudo apt update")):
			error(f"@TODO: error message")


def install_local_bin(src:str, name:str):
	dst = f"{os.environ["HOME"]}/.local/bin/{name}"

	if not os.path.exists(dst):
		prompt_process([ "ln", "-s", src, dst ])


def install_mxe_bin(src:str, name:str):
	dst = f"{MXE_DIRECTORY}/usr/bin/{MXE_PREFIX}.static-{name}"

	if not os.path.exists(dst):
		prompt_process([ "ln", "-s", src, dst ])


def strip_arch(input:str)->str:
	return input if input.find(":") < 0 else input[:input.find(":")]


def install_path():
	# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
	# @TODO: Proper monkey programming. Should probably handle    #
	#        this more elegantly.                                 #
	# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
	with open(f"{os.environ["HOME"]}/.bashrc", "r") as f:
		bashrc = f.read()

	for line in bashrc.splitlines():
		if line == f"export PATH=$PATH:{MXE_DIRECTORY}/usr/bin":
			return

	with open(f"{os.environ["HOME"]}/.bashrc", "w") as f:
		f.write(bashrc)
		f.write(f"\nexport PATH=$PATH:{MXE_DIRECTORY}/usr/bin\n")


def write_mxe_makefile(name:str, make:str):
	with open_and_write_on_change(f"src/{name}.mk") as f:
		f.write(make)


def main():
	# Avoid sudo
	assert os.getuid() != 0

	# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
	# @TODO: Currently installs version 21 by default.            #
	#        Will break once +22 is available.                    #
	#        Replace argument with LLVM_VERSION to fix.           #
	# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
	install_llvm_repository("")

	proc = subprocess.run(["dpkg", "-l"] + APT_PACKAGES, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
	dpkg = proc.stdout.decode('utf-8').strip()
	installed_packages = [ strip_arch(list[1]) for list in [row.split() for row in dpkg.splitlines()] if len(list) >= 4 ]
	missing_packages = [pkg for pkg in APT_PACKAGES if pkg not in installed_packages]

	if len(missing_packages) > 0:
		if not prompt_process(["sudo", "apt", "install"] + missing_packages):
			print("skipped necessary package installation.")
			exit(1)

	install_local_bin(f"/usr/bin/clang-{LLVM_VERSION}", "clang")
	install_local_bin(f"/usr/bin/clangd-{LLVM_VERSION}", "clangd")
	install_local_bin(f"/usr/bin/llvm-strip-{LLVM_VERSION}", "llvm-strip")
	install_local_bin(f"/usr/bin/ld.lld-{LLVM_VERSION}", "ld.lld")

	if not os.path.exists(MXE_DIRECTORY):
		# Make sure the user has access to MXE_DIRECTORY
		if (not prompt_process([ "sudo", "mkdir", MXE_DIRECTORY ]) or
			not prompt_process_shell(f'sudo chown "$USER":"$(id -gn)" {MXE_DIRECTORY}')):
			error(f"@TODO: error message")

	if not os.path.exists(f"{MXE_DIRECTORY}/settings.mk"):
		if not prompt_process([ "git", "clone", "--depth=1", "https://github.com/mxe/mxe.git", MXE_DIRECTORY ]):
			error(f"@TODO: error message")

	os.chdir(MXE_DIRECTORY)
	
	# Update SDL3
	write_mxe_makefile("sdl3",
		"PKG             := sdl3\n"
		"$(PKG)_WEBSITE  := https://www.libsdl.org/\n"
		"$(PKG)_DESCR    := SDL3\n"
		"$(PKG)_IGNORE   :=\n"
		"$(PKG)_VERSION  := 3.2.16\n"
		"$(PKG)_SUBDIR   := SDL-release-$($(PKG)_VERSION)\n"
		"$(PKG)_FILE     := SDL3-$($(PKG)_VERSION).tar.gz\n"
		"$(PKG)_CHECKSUM := a1af401fb49b824ba721683862439e014498f79753602827e174f3613357aff0\n"
		"$(PKG)_GH_CONF  := libsdl-org/SDL/releases/tag,release-,,\n"
		"$(PKG)_DEPS     := cc libiconv libsamplerate\n"
		"define $(PKG)_BUILD\n"
		"    cd '$(BUILD_DIR)' && $(TARGET)-cmake '$(SOURCE_DIR)' \\\n"
		"        -DSDL_SHARED=$(CMAKE_SHARED_BOOL) \\\n"
		"        -DSDL_STATIC=$(CMAKE_STATIC_BOOL) \\\n"
		"        -DVERBOSE=1\n"
		"    $(MAKE) -C '$(BUILD_DIR)' -j '$(JOBS)'\n"
		"    $(MAKE) -C '$(BUILD_DIR)' -j 1 install\n"
		"    '$(TARGET)-gcc' \\\n"
		"        -W -Wall -Werror -ansi -pedantic \\\n"
		"        '$(TEST_FILE)' -o '$(PREFIX)/$(TARGET)/bin/test-sdl3.exe' \\\n"
		"        `'$(TARGET)-pkg-config' sdl3 --cflags --libs`\n"
		"endef")

	# Add jemalloc: better than mingw32 libc allocators
	write_mxe_makefile("jemalloc",
		"PKG             := jemalloc\n"
		"$(PKG)_WEBSITE  := github.com\n"
		"$(PKG)_DESCR    := jemalloc\n"
		"$(PKG)_IGNORE   :=\n"
		"$(PKG)_VERSION  := 5.3.0\n"
		"$(PKG)_CHECKSUM := ef6f74fd45e95ee4ef7f9e19ebe5b075ca6b7fbe0140612b2a161abafb7ee179\n"
		"$(PKG)_GH_CONF  := jemalloc/jemalloc/tags\n"
		"$(PKG)_DEPS     := cc\n"
		"\n"
		"define $(PKG)_BUILD\n"
		"	cd '$(SOURCE_DIR)' && autoconf\n"
		"	cd '$(BUILD_DIR)' && '$(SOURCE_DIR)/configure' \\\n"
		"		$(MXE_CONFIGURE_OPTS)\n"
		"	$(MAKE) -C '$(BUILD_DIR)' -j '$(JOBS)'\n"
		"	$(MAKE) -C '$(BUILD_DIR)' -j 1 install\n"
		"endef")

	# Fix libdwarf: cpptrace dependency
	write_mxe_makefile("libdwarf",
		"PKG := libdwarf\n"
		"$(PKG)_WEBSITE  := https://www.prevanders.net/\n"
		"$(PKG)_IGNORE   :=\n"
		"$(PKG)_VERSION  := 0.9.2\n"
		"$(PKG)_CHECKSUM := 22b66d06831a76f6a062126cdcad3fcc58540b89a1acb23c99f8861f50999ec3\n"
		"$(PKG)_SUBDIR   := libdwarf-$($(PKG)_VERSION)\n"
		"$(PKG)_FILE     := libdwarf-$($(PKG)_VERSION).tar.xz\n"
		"$(PKG)_URL      := https://www.prevanders.net/$($(PKG)_FILE)\n"
		"$(PKG)_DEPS     := cc zlib zstd\n"
		"\n"
		"define $(PKG)_BUILD\n"
		"	cd '$(BUILD_DIR)' && $(TARGET)-cmake '$(SOURCE_DIR)' \\n"
		"		-DCMAKE_BUILD_TYPE=Release \\n"
		"		-DBUILD_SHARED=$(CMAKE_SHARED_BOOL) \\n"
		"		-DBUILD_STATIC=$(CMAKE_STATIC_BOOL)\n"
		"	$(MAKE) -C '$(BUILD_DIR)' -j '$(JOBS)'\n"
		"	$(MAKE) -C '$(BUILD_DIR)' -j 1 install\n"
		"endef\n")

	# Add cpptrace: nice debugging
	write_mxe_makefile("cpptrace",
		"PKG             := cpptrace\n"
		"$(PKG)_WEBSITE  := https://github.com/jeremy-rifkin/$(PKG)\n"
		"$(PKG)_DESCR    := cpptrace\n"
		"$(PKG)_IGNORE   :=\n"
		"$(PKG)_VERSION  := 0.7.2\n"
		"$(PKG)_CHECKSUM := 62835abfd91a840e4d212c850695b576523fe6f9036bc5c3e52183b6eb9905c5\n"
		"$(PKG)_GH_CONF  := jeremy-rifkin/cpptrace/releases,v\n"
		"$(PKG)_DEPS     := cc libdwarf zstd zlib\n"
		"\n"
		"define $(PKG)_BUILD\n"
		"	cd '$(BUILD_DIR)' && $(TARGET)-cmake '$(SOURCE_DIR)' \\\n"
		"		-DCPPTRACE_USE_EXTERNAL_LIBDWARF=On \\\n"
		"		-DCPPTRACE_UNWIND_WITH_WINAPI=On \\\n"
		"		-DCPPTRACE_GET_SYMBOLS_WITH_LIBDWARF=On \\\n"
		"		-DCPPTRACE_DEMANGLE_WITH_CXXABI=On \\\n"
		"		-DBUILD_SHARED=$(CMAKE_SHARED_BOOL) \\\n"
		"		-DBUILD_STATIC=$(CMAKE_STATIC_BOOL) \\\n"
		"		-DCPPTRACE_STATIC_DEFINE=On \\\n"
		"		-DCMAKE_CXX_STANDARD=23\n"
		"	$(MAKE) -C '$(BUILD_DIR)' -j '$(JOBS)'\n"
		"	$(MAKE) -C '$(BUILD_DIR)' -j 1 install\n"
		"endef\n")

	# Patch for preventing ident spam from GCC
	with open_and_write_on_change("plugins/gcc14/ident.patch") as f:
		f.write(
			'--- "a/gcc/toplev.cc"\n'
			'+++ "b/gcc/toplev.cc"\n'
			'@@ -560,7 +560,7 @@\n'
			'   /* Attach a special .ident directive to the end of the file to identify\n'
			'      the version of GCC which compiled this code.  The format of the .ident\n'
			'      string is patterned after the ones produced by native SVR4 compilers.  */\n'
			'-  if (!flag_no_ident)\n'
			'+  if (false)\n'
			'     {\n'
			'       const char *pkg_version = "(GNU) ";\n'
			'       char *ident_str;\n'
			'\n'
			'--- "a/gcc/c-family/c-lex.cc"\n'
			'+++ "b/gcc/c-family/c-lex.cc"\n'
			'@@ -167,7 +167,7 @@\n'
			' \t  unsigned int ARG_UNUSED (line),\n'
			' \t  const cpp_string * ARG_UNUSED (str))\n'
			' {\n'
			'-  if (!flag_no_ident)\n'
			'+  if (false)\n'
			'     {\n'
			'       /* Convert escapes in the string.  */\n'
			'       cpp_string cstr = { 0, 0 };\n\n')

	# Inject patch to GCC-14. There's no particular reason
	# for choosing version 14.
	with open_and_write_on_change("plugins/gcc14/gcc14-overlay.mk") as f:
		f.write(
			"PKG             := gcc\n"
			"# version used for tarball, will be X-YYYYMMDD for snapshots\n"
			"$(PKG)_VERSION  := 14.2.0\n"
			"# release used for install dirs, will be X.0.1 for snapshots\n"
			"# change to $($(PKG)_VERSION) variable on release X.Y[>0].Z\n"
			"$(PKG)_RELEASE  := $($(PKG)_VERSION)\n"
			"$(PKG)_CHECKSUM := a7b39bc69cbf9e25826c5a60ab26477001f7c08d85cec04bc0e29cabed6f3cc9\n"
			"$(PKG)_SUBDIR   := gcc-$($(PKG)_VERSION)\n"
			"$(PKG)_FILE     := gcc-$($(PKG)_VERSION).tar.xz\n"
			"$(PKG)_URL      := https://ftp.gnu.org/gnu/gcc/gcc-$($(PKG)_VERSION)/$($(PKG)_FILE)\n"
			"$(PKG)_URL_2    := https://www.mirrorservice.org/sites/sourceware.org/pub/gcc/snapshots/$($(PKG)_VERSION)/$($(PKG)_FILE)\n"
			"$(PKG)_PATCHES  := $(dir $(lastword $(MAKEFILE_LIST)))/gcc14.patch $(dir $(lastword $(MAKEFILE_LIST)))/ident.patch\n"
			"$(PKG)_DEPS     := binutils mingw-w64 $(addprefix $(BUILD)~,gmp isl mpc mpfr zstd)\n"
			"\n"
			"_$(PKG)_CONFIGURE_OPTS = --with-zstd='$(PREFIX)/$(BUILD)'\n"
			"\n"
			"# copy db-2-install-exe.patch to gcc7 plugin when gcc10 is default\n"
			"db_PATCHES := $(TOP_DIR)/src/db-1-fix-including-winioctl-h-lowcase.patch\n"
			"\n"
			"# set these in respective makefiles when gcc10 becomes default\n"
			"# remove from here and leave them blank for gcc5 plugin\n"
			"libssh_EXTRA_WARNINGS = -Wno-error=implicit-fallthrough\n"
			"gtkimageview_EXTRA_WARNINGS = -Wno-error=misleading-indentation\n"
			"guile_EXTRA_WARNINGS = -Wno-error=misleading-indentation\n"
			"gtkmm2_EXTRA_WARNINGS = -Wno-error=cast-function-type\n"
			"gtkmm3_EXTRA_WARNINGS = -Wno-error=cast-function-type\n"
			"gtkglextmm_EXTRA_WARNINGS = -Wno-error=cast-function-type\n")

	# Self generate suitable settings. I guess the JOBS count
	# could use some sophisticated formula to spare some
	# threads but I guess it'll do for now.
	with open_and_write_on_change("settings.mk") as f:
		f.write(
			f'JOBS                     := {os.cpu_count()}\n'
			f'MXE_TARGETS              := {MXE_PREFIX}.static\n'
			 'override MXE_PLUGIN_DIRS += plugins/gcc14\n')


	print("Make MXE")
	additional_packages = sys.argv[1:]
	subprocess.run([ "make" ] + MXE_PACKAGES + additional_packages, check=True)

	install_mxe_bin(f"/usr/bin/clang-{LLVM_VERSION}", "clang")
	install_mxe_bin(f"/usr/bin/llvm-strip-{LLVM_VERSION}", "llvm-strip")
	install_mxe_bin(f"/usr/bin/ld.lld-{LLVM_VERSION}", "ld.lld")
	install_path()

	# Hack of sorts to get proper error on some linking cases
	if not os.path.exists(f"usr/{MXE_PREFIX}.static/lib/libgcc_s.a"):
		subprocess.run([
			f"usr/bin/{MXE_PREFIX}.static-ar",
			 "rsc",
			f"usr/{MXE_PREFIX}.static/lib/libgcc_s.a",
		], check=True)
	if not os.path.exists(f"usr/{MXE_PREFIX}.static/lib/libgcc_eh.a"):
		subprocess.run([
			f"usr/bin/{MXE_PREFIX}.static-ar",
			 "rsc",
			f"usr/{MXE_PREFIX}.static/lib/libgcc_eh.a",
		], check=True)


	# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
	# @TODO: look into ways of building jemalloc without it       #
	#        producing a massive .lib file.                       #
	# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
	if os.path.exists(f"usr/{MXE_PREFIX}.static/lib/jemalloc_s.lib"):
		subprocess.run([
			 "cp",
			f"usr/{MXE_PREFIX}.static/lib/jemalloc.lib",
			f"usr/{MXE_PREFIX}.static/lib/jemalloc-backup.lib"
		])
		subprocess.run([
			 "rm",
			f"usr/{MXE_PREFIX}.static/lib/jemalloc_s.lib",
		])
		subprocess.run([
			f"llvm-strip-{LLVM_VERSION}",
			 "--strip-debug",
			f"usr/{MXE_PREFIX}.static/lib/jemalloc.lib"
		])


if __name__ == "__main__":
	main()
