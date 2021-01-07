from conans import ConanFile, Meson, tools
from conans.errors import ConanInvalidConfiguration
import os


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
        self.build_requires("meson/0.56.0")
        if not tools.which('pkg-config'):
            self.build_requires("pkgconf/1.7.3")
    
    def requirements(self):
        self.requires("gdk-pixbuf/2.42.0")
        self.requires("glib/2.67.0")
        self.requires("cairo/1.17.2")
        self.requires("graphene/1.10.2")
        if self.settings.os == "Linux":
            self.requires("xkbcommon/1.0.3")
            if self.options.with_wayland:
                self.requires("wayland") # FIXME: Create an actual Wayland package(s)
            if self.options.with_x11:
                self.requires("xorg/system")
        self.requires("libepoxy/1.5.4")
        if self.options.with_pango:
            self.requires("pango/1.48.0")

    def system_requirements(self):
        if self.settings.os == 'Linux' and tools.os_info.is_linux:
            if tools.os_info.with_apt:
                installer = tools.SystemPackageTool()
                packages = ['sassc']
                for package in packages:
                    installer.install(package)

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
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_meson(self):
        meson = Meson(self)
        defs = {}
        if self.settings.os == "Linux":
            defs["wayland-backend"] = "true" if self.options.with_wayland else "false"
            defs["x11-backend"] = "true" if self.options.with_x11 else "false"
        defs["introspection"] = "disabled"
        defs["documentation"] = "false"
        defs["man-pages"] = "false"
        defs["build-tests"] = "false"
        defs["build-examples"] = "false"
        defs["demos"] = "false"
        args=[]
        args.append("--wrap-mode=nofallback")
        meson.configure(defs=defs, build_folder=self._build_subfolder, source_folder=self._source_subfolder, pkg_config_paths=[self.install_folder], args=args)
        return meson

    def build(self):
        with tools.environment_append(tools.RunEnvironment(self).vars):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)
        meson = self._configure_meson()
        with tools.environment_append({
            "PKG_CONFIG_PATH": self.install_folder,
            "PATH": [os.path.join(self.package_folder, "bin")]}):
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
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.includedirs.append(os.path.join("include", "gtk-4.0"))
        self.cpp_info.names["pkg_config"] = "gtk+-3.0"
        if self.settings.os == "Macos":
            self.cpp_info.frameworks = ["AppKit", "Carbon"]
