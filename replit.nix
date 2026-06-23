{pkgs}: {
  deps = [
    pkgs.libffi
    pkgs.glib
    pkgs.gdk-pixbuf
    pkgs.cairo
    pkgs.fontconfig
    pkgs.harfbuzz
    pkgs.pango
    pkgs.redis
    pkgs.mongodb
  ];
}
