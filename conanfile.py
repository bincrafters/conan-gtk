from conans import ConanFile, Meson, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil


class LibnameConan(ConanFile):
    name = "gtk"
    description = "libraries used for creating graphical user interfaces for applications."
    topics = ("conan", "gtk", "widgets")
    url = "https://github.com/bincrafters/conan-gtk"
    homepage = "https://www.gtk.org/"
    license = "LGPL-2.1"
    generators = "pkg_config"

    # Options may need to change depending on the packaged library
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_wayland": [True, False],
        "with_x11": [True, False],
        "with_pango": [True, False]
        }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_wayland": False,
        "with_x11": True,
        "with_pango": True}

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC
        if self.settings.os != 'Linux':
            del self.options.with_wayland
            del self.options.with_x11
    
    def build_requirements(self):
        self.build_requires('meson/0.53.0')
        #self.build_requires('pkg-config_installer/0.29.2@bincrafters/stable')
    
    def requirements(self):
        self.requires("gdk-pixbuf/2.40.0@bincrafters/stable")
        if self.settings.compiler != 'Visual Studio':
            self.requires("cairo/1.17.2@bincrafters/stable")
        if self.settings.os == 'Linux':
            self.requires("at-spi2-atk/2.34.1@bincrafters/stable")
            if self.options.with_wayland:
                self.requires("xkbcommon/0.9.1@bincrafters/stable")
                self.requires("wayland")
            if self.options.with_x11:
                self.requires("libxrandr/1.5.2@bincrafters/stable")
                self.requires("libxrender/0.9.10@bincrafters/stable")
                self.requires("libx11/1.6.8@bincrafters/stable")
                self.requires("libxi/1.7.10@bincrafters/stable")
                self.requires("libxext/1.3.4@bincrafters/stable")
                self.requires("libxcursor/1.2.0@bincrafters/stable")
                self.requires("libxdamage/1.1.5@bincrafters/stable")
                self.requires("libxfixes/5.0.3@bincrafters/stable")
                self.requires("libxcomposite/0.4.5@bincrafters/stable")
                self.requires("fontconfig/2.13.91@conan/stable")
                self.requires("libxinerama/1.1.4@bincrafters/stable")
        self.requires("libepoxy/1.5.4@bincrafters/stable")
        if self.options.with_pango:
            self.requires("pango/1.44.7@bincrafters/stable")

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        if self.settings.os == 'Linux':
            if self.options.with_wayland or self.options.with_x11:
                if not self.options.with_pango:
                    raise ConanInvalidConfiguration('with_pango option is mandatory when with_wayland or with_x11 is used')

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir.replace('gtk', 'gtk+'), self._source_subfolder)

    def _configure_meson(self):
        meson = Meson(self)
        defs = {}
        if self.settings.os == 'Linux':
            defs['wayland_backend'] = 'true' if self.options.with_wayland else 'false'
            defs['x11_backend'] = 'true' if self.options.with_x11 else 'false'
        defs['introspection'] = 'false'
        defs['documentation'] = 'false'
        defs['man-pages'] = 'false'
        defs['tests'] = 'false'
        defs['examples'] = 'false'
        defs['demos'] = 'false'
        args=[]
        args.append('--wrap-mode=nofallback')
        meson.configure(defs=defs, build_folder=self._build_subfolder, source_folder=self._source_subfolder, pkg_config_paths=[self.install_folder], args=args)
        return meson

    def build(self):
        for package in self.deps_cpp_info.deps:
            lib_path = self.deps_cpp_info[package].rootpath
            for dirpath, _, filenames in os.walk(lib_path):
                for filename in filenames:
                    if filename.endswith('.pc'):
                        if filename in ["cairo.pc", "fontconfig.pc", "xext.pc", "xi.pc", "x11.pc", "xcb.pc"]:
                            continue
                        shutil.copyfile(os.path.join(dirpath, filename), filename)
                        tools.replace_prefix_in_pc_file(filename, lib_path)
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
        self.cpp_info.libs = [l for l in tools.collect_libs(self) if not l.startswith('im-')]
        self.cpp_info.includedirs.append(os.path.join('include', 'gtk-3.0'))
        self.cpp_info.includedirs.append(os.path.join('include', 'gail-3.0'))
        self.cpp_info.names['pkg_config'] = 'gtk+-3.0'
