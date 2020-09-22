from conans import ConanFile, Meson, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil


class LibnameConan(ConanFile):
    name = "gtk"
    description = "libraries used for creating graphical user interfaces for applications."
    topics = ("conan", "gtk", "widgets")
    url = "https://github.com/bincrafters/conan-gtk"
    homepage = "https://www.gtk.org"
    license = "LGPL-2.1-or-later"
    generators = "pkg_config"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_wayland": [True, False],
        "with_x11": [True, False],
        "with_pango": [True, False]
        }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_wayland": False,
        "with_x11": True,
        "with_pango": True}

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_wayland
            del self.options.with_x11
    
    def build_requirements(self):
        self.build_requires("meson/0.54.2")
        if not tools.which('pkg-config'):
            self.build_requires("pkgconf/1.7.3")
    
    def requirements(self):
        self.requires("gdk-pixbuf/2.40.0@bincrafters/stable")
        if self.settings.compiler != "Visual Studio":
            self.requires("cairo/1.17.2@bincrafters/stable")
        if self.settings.os == "Linux":
            self.requires("at-spi2-atk/2.34.2@bincrafters/stable")
            self.requires("glib/2.66.0")
            if self.options.with_wayland:
                self.requires("xkbcommon/0.10.0")
                self.requires("wayland") # FIXME: Create an actual Wayland package(s)
            if self.options.with_x11:
                self.requires("xorg/system")
        self.requires("atk/2.36.0@bincrafters/stable")
        self.requires("libepoxy/1.5.4")
        if self.options.with_pango:
            self.requires("pango/1.46.1@bincrafters/stable")

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.settings.os == "Linux":
            if self.options.with_wayland or self.options.with_x11:
                if not self.options.with_pango:
                    raise ConanInvalidConfiguration("with_pango option is mandatory when with_wayland or with_x11 is used")
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("GTK recipe is not yet compatible with Windows. Contributions are welcome.")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir.replace("gtk", "gtk+"), self._source_subfolder)

    def _configure_meson(self):
        meson = Meson(self)
        defs = {}
        if self.settings.os == "Linux":
            defs["wayland_backend"] = "true" if self.options.with_wayland else "false"
            defs["x11_backend"] = "true" if self.options.with_x11 else "false"
        defs["introspection"] = "false"
        defs["documentation"] = "false"
        defs["man-pages"] = "false"
        defs["tests"] = "false"
        defs["examples"] = "false"
        defs["demos"] = "false"
        args=[]
        args.append("--wrap-mode=nofallback")
        meson.configure(defs=defs, build_folder=self._build_subfolder, source_folder=self._source_subfolder, pkg_config_paths=[self.install_folder], args=args)
        return meson

    def build(self):
        for package in self.deps_cpp_info.deps:
            lib_path = self.deps_cpp_info[package].rootpath
            for dirpath, _, filenames in os.walk(lib_path):
                for filename in filenames:
                    if filename.endswith(".pc"):
                        if filename in ["cairo.pc", "fontconfig.pc", "xext.pc", "xi.pc", "x11.pc", "xcb.pc"]:
                            continue
                        shutil.copyfile(os.path.join(dirpath, filename), filename)
                        tools.replace_prefix_in_pc_file(filename, lib_path)
        tools.replace_in_file(os.path.join(self._source_subfolder, 'meson.build'), "\ntest(\n", "\nfalse and test(\n")
        with tools.environment_append(tools.RunEnvironment(self).vars):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        meson = self._configure_meson()
        meson.install()
        # If the CMakeLists.txt has a proper install method, the steps below may be redundant
        # If so, you can just remove the lines below
        include_folder = os.path.join(self._source_subfolder, "include")
        self.copy(pattern="*", dst="include", src=include_folder)
        self.copy(pattern="*.dll", dst="bin", keep_path=False)
        self.copy(pattern="*.lib", dst="lib", keep_path=False)
        self.copy(pattern="*.a", dst="lib", keep_path=False)
        self.copy(pattern="*.so*", dst="lib", keep_path=False)
        self.copy(pattern="*.dylib", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["gailutil-3", "gtk-3", "gdk-3"]
        self.cpp_info.includedirs.append(os.path.join("include", "gtk-3.0"))
        self.cpp_info.includedirs.append(os.path.join("include", "gail-3.0"))
        self.cpp_info.names["pkg_config"] = "gtk+-3.0"
        if self.settings.os == "Macos":
            self.cpp_info.frameworks = ["AppKit", "Carbon"]
