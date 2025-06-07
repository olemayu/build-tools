INFO_NAME    := $(shell sed -n '1p' configs/info)
INFO_PREFIX  := $(shell sed -n '2p' configs/info)
INFO_VER     := $(shell sed -n '3p' configs/info)
INFO_HASH    := $(shell git rev-parse --short HEAD)
PWD          := $(shell pwd)

MAKE_TARGET  := $(shell echo $(make_target) | tr a-z A-Z)
MAKE_CONFIG  := $(shell echo $(make_config) | tr a-z A-Z)

BINARY_PATH  := bin/$(make_target)-$(make_config)
BUILD_PATH   := bin/build/$(make_target)-$(make_config)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

BUILD_DEPENDENCIES := $(shell find configs -type f -name '*.mk') \
                      configs/info

define FN_SOURCE_TO_OBJ
$($(1):source/%.c=$(BINARY_PATH)/$(2)/%.o)
endef

define FN_BUILD_OBJ_RECIPE
$(BINARY_PATH)/$(1)/%.o: source/%.c $(BUILD_DEPENDENCIES)
endef

define FN_PRINT
printf "\e[38;2;%s;%s;%sm%s \e[0;90m%s\e[m%s\n" $(1) $(2) $(3) $(4) $(dir $@) $(notdir $@)
endef

define FN_COMPILE_CC
	@mkdir -p $(@D)
	@$(call FN_PRINT,0,168,160,cc)
	@$(CC) -MMD -c $< -o $@ $(CFLAGS) $(SECRET_CFLAGS)
endef

STRIP_DEVELOPMENT =
STRIP_RELEASE     = llvm-strip --strip-all $@

define FN_COPY
	@mkdir -p $(dir $(1))
	@$(call FN_PRINT,187,224,0,copy)
	@cp $@ $(1)
endef

define FN_LINK
	@mkdir -p $(@D)
	@$(call FN_PRINT,255,204,0,ld)
	@$(CC) $(1) $(MAIN_LDFLAGS) $(LDFLAGS_TARGET) $(LDFLAGS_CONFIG) $(LDFLAGS_TARGET_$(MAKE_CONFIG)) $(LDFLAGS) $(2) -o $@
	$(STRIP_$(MAKE_CONFIG))
	$(call FN_COPY,$(BUILD_PATH)/$(notdir $@))
endef

IMPL_EXPORT_WIN32 = -shared -Wl,--out-implib,lib$(1).a
IMPL_IMPORT_WIN32 = -L. -l$(1)
IMPL_EXPORT_LINUX = -shared
IMPL_IMPORT_LINUX = -Wl,-rpath,. "-L$(BINARY_PATH)" -l$(1)

define FN_EXPORT
$(IMPL_EXPORT_$(MAKE_TARGET))
endef

define FN_IMPORT
$(IMPL_IMPORT_$(MAKE_TARGET))
endef

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

SOURCE_ALL      := $(shell find source -type f -name '*.c')
SOURCE_COMMON   := $(filter-out %.linux.c %.win32.c,$(SOURCE_ALL))
SOURCE_PLATFORM := $(filter %.linux.c %.win32.c,$(SOURCE_ALL))
SOURCE          := $(SOURCE_COMMON) $(filter %.$(make_target).c,$(SOURCE_PLATFORM))

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

MAIN_CFLAGS         := -Isource \
                       -Iinclude \
                       -D$(INFO_PREFIX)_NAME=\"$(INFO_NAME)\" \
                       -D$(INFO_PREFIX)_HASH=\"$(INFO_HASH)\" \
                       -D$(INFO_PREFIX)_TARGET=$(make_target) \
                       -D$(INFO_PREFIX)_CONFIG=$(make_config) \
                       -D$(INFO_PREFIX)_VERSION=$(INFO_VER) \
                       "-fdebug-prefix-map=$(PWD)=" \
                       -std=gnu2y \
                       -O3 \
                       -Wall \
                       -Wextra \
                       -Werror=format \
                       -Werror=shadow \
                       -Werror=switch \
                       -Werror=return-type \
                       -Werror=sign-compare \
                       -Werror=unused-result \
                       -Werror=implicit-fallthrough \
                       -Werror=incompatible-pointer-types \
                       -Wno-gcc-compat \
                       -Wno-nullability-completeness \
                       -Wno-deprecated-octal-literals \
                       -ffast-math \
                       -fno-exceptions \
                       -fms-extensions \
                       -funsigned-char \
                       -mno-ms-bitfields
MAIN_LDFLAGS        := -lm \
                       -pthread \
                       -fuse-ld=lld
CFLAGS_DEVELOPMENT  := -gdwarf-4 \
                       -fno-omit-frame-pointer \
                       -D$(INFO_PREFIX)_DEVELOPMENT=1 \
                       -D$(INFO_PREFIX)_RELEASE=0
LDFLAGS_DEVELOPMENT := -fno-omit-frame-pointer

CFLAGS_RELEASE      := -ffast-math \
                       -fdata-sections \
                       -ffunction-sections \
                       -DNDEBUG=1 \
                       -D$(INFO_PREFIX)_DEVELOPMENT=0 \
                       -D$(INFO_PREFIX)_RELEASE=1
LDFLAGS_RELEASE     := -Wl,--gc-sections

# These will not be written into .clangd config
SECRET_CFLAGS       := -Wno-unused-parameter \
                       -Wno-unused-function

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

EXE_WIN32           := exe
DLL_WIN32           := dll
CC_WIN32            := x86_64-w64-mingw32.static-clang
CXX_WIN32           := x86_64-w64-mingw32.static-clang++
PKGCONFIG_WIN32     := x86_64-w64-mingw32.static-pkg-config
CFLAGS_WIN32        := -D$(INFO_PREFIX)_LINUX=0 -D$(INFO_PREFIX)_WIN32=1 -D$(INFO_PREFIX)_TRACE_SKIP=4
LDFLAGS_WIN32       := -Wl,-stack=0x800000

EXE_LINUX           := elf
DLL_LINUX           := so
CC_LINUX            := clang
CXX_LINUX           := clang++
PKGCONFIG_LINUX     := pkg-config
CFLAGS_LINUX        := -D$(INFO_PREFIX)_LINUX=1 -D$(INFO_PREFIX)_WIN32=0 -D$(INFO_PREFIX)_TRACE_SKIP=3
LDFLAGS_LINUX       := -Wl,-z,stack-size=0x800000

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

EXE                 := $(EXE_$(MAKE_TARGET))
DLL                 := $(DLL_$(MAKE_TARGET))
CC                  := $(CC_$(MAKE_TARGET))
CXX                 := $(CXX_$(MAKE_TARGET))
PKGCONFIG           := $(PKGCONFIG_$(MAKE_TARGET))

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

CFLAGS += $(MAIN_CFLAGS) $(CFLAGS_$(MAKE_TARGET)) $(CFLAGS_$(MAKE_CONFIG))

ifeq ($(MAKE_TARGET),LINUX)
ifeq ($(MAKE_CONFIG),DEVELOPMENT)
CFLAGS  += -fsanitize=address
LDFLAGS += -fsanitize=address
endif
endif

$(BINARY_PATH)/static/%.o:            CFLAGS += -D$(INFO_PREFIX)_STATIC=1 -D$(INFO_PREFIX)_SHARED=0
$(BINARY_PATH)/shared/%.o:            CFLAGS += -D$(INFO_PREFIX)_STATIC=0 -D$(INFO_PREFIX)_SHARED=1 -fPIC
$(BINARY_PATH)/persistent-static/%.o: CFLAGS += -D$(INFO_PREFIX)_STATIC=1 -D$(INFO_PREFIX)_SHARED=0
$(BINARY_PATH)/persistent-shared/%.o: CFLAGS += -D$(INFO_PREFIX)_STATIC=0 -D$(INFO_PREFIX)_SHARED=1 -fPIC

-include configs/override.mk
-include configs/override.$(make_target).mk
include configs/make.$(make_build).mk

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

OBJECTS      := $(call FN_SOURCE_TO_OBJ,SOURCE_ALL,static) $(call FN_SOURCE_TO_OBJ,SOURCE_ALL,shared) $(call FN_SOURCE_TO_OBJ,SOURCE_ALL,persistent-static) $(call FN_SOURCE_TO_OBJ,SOURCE_ALL,persistent-shared)
DEPENDENCIES := $(OBJECTS:%.o=%.d)

-include $(DEPENDENCIES)

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

default: $(BUILD_PRODUCTS)

execute: $(BUILD_PRODUCTS)
	cd $(BUILD_PATH) && ./$(BUILD_MAIN)

clean:
	rm -rf $(BUILD_PATH) $(BUILD_PRODUCTS) $(BUILD_CLEAN) bin/*/static bin/*/shared

clean-all:
	rm -rf $(BUILD_PATH) $(BUILD_PRODUCTS) $(BUILD_CLEAN) bin

flags:
	@echo $(CFLAGS) > $(make_target).$(make_config).cflags

$(call FN_BUILD_OBJ_RECIPE,static)
	$(FN_COMPILE_CC)
$(call FN_BUILD_OBJ_RECIPE,shared)
	$(FN_COMPILE_CC)
$(call FN_BUILD_OBJ_RECIPE,persistent-static)
	$(FN_COMPILE_CC)
$(call FN_BUILD_OBJ_RECIPE,persistent-shared)
	$(FN_COMPILE_CC)
%.vert.spirv: %.vert.glsl
	@$(call FN_PRINT,235,120,20,glsl)
	@glslc -fshader-stage=vert -O $< -o $@
%.frag.spirv: %.frag.glsl
	@$(call FN_PRINT,235,120,20,glsl)
	@glslc -fshader-stage=frag -O $< -o $@
