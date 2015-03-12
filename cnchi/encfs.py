#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# encfs.py
#
#  Copyright © 2013,2014 Antergos
#
#  This file is part of Cnchi.
#
#  Cnchi is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  Cnchi is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Cnchi; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

""" Configures Antergos to encrypt user's home with encFS """

import os
import shutil
import subprocess
import logging
import misc.misc as misc

# TODO: This is unfinished and untested


@misc.raise_privileges
def backup_conf_files(dest_dir):
    conf_files = [
        "etc/security/pam_encfs.conf",
        "etc/security/pam_env.conf",
        "etc/fuse.conf",
        "etc/pam.d/system-login",
        "etc/pam.d/system-auth"]
    for conf_file in conf_files:
        path = os.path.join(dest_dir, conf_file)
        if os.path.exists(path):
            shutil.copy(path, path + ".cnchi")
    os.system("sync")


@misc.raise_privileges
def setup_conf_files(dest_dir):
    path = os.path.join(dest_dir, "etc/security/pam_encfs.conf")
    with open(path, 'w') as pam_encfs:
        pam_encfs.write("# File created by Cnchi (Antergos Installer)\n\n")
        pam_encfs.write("# If this is specified program will attempt to drop permissions before running encfs.\n")
        pam_encfs.write("drop_permissions\n\n")
        pam_encfs.write("# This specifies which options to pass to encfs for every user.\n")
        pam_encfs.write("# You can find encfs options by running encfs without any arguments\n")
        pam_encfs.write("encfs_default --idle=1\n\n")
        pam_encfs.write("# Same for fuse\n")
        pam_encfs.write("# you can find fuse options with encfs -H\n")
        pam_encfs.write("fuse_default allow_root,nonempty\n\n")
        pam_encfs.write("# Added by Cnchi - Antergos Installer\n")
        # USERNAME SOURCE TARGET_PATH ENCFS_Options FUSE_Options
        pam_encfs.write("-\t/home/.encfs\t-\t-v\t-\n")

    path = os.path.join(dest_dir, "etc/security/pam_env.conf")
    with open(path, 'a') as pam_env:
        pam_env.write("\n# Added by Cnchi - Antergos Installer\n")
        pam_env.write("# Set the ICEAUTHORITY file location to allow GNOME to start on encfs $HOME\n")
        pam_env.write("ICEAUTHORITY DEFAULT=/tmp/.ICEauthority_@{PAM_USER}\n")

    path = os.path.join(dest_dir, "etc/fuse.conf")
    with open(path, 'a') as fuse_conf:
        fuse_conf.write("\n# Added by Cnchi - Antergos Installer\n")
        fuse_conf.write("user_allow_other\n")

    path = os.path.join(dest_dir, "etc/pam.d/system-login")
    with open(path, 'a') as system_login:
        system_login.write("\n# Added by Cnchi - Antergos Installer\n")
        system_login.write("session required\tpam_encfs.so\n")
        system_login.write("session optional\tpam_mount.so\n")

    path = os.path.join(dest_dir, "etc/pam.d/system-auth")
    with open(path, "a") as system_auth:
        system_auth.write("\n# Added by Cnchi - Antergos Installer\n")
        system_auth.write("auth sufficient\tpam_encfs.so\n")
        system_auth.write("auth optional\tpam_mount.so\n")


@misc.raise_privileges
def setup(username, dest_dir, password):
    """ Encrypt user's home folder """
    # encfs and pam_mount packages are needed
    # and pam_encfs from AUR, too.
    # Reference: https://wiki.debian.org/TransparentEncryptionForHomeFolder

    try:
        backup_conf_files(dest_dir)
        setup_conf_files(dest_dir)
    except Exception as general_error:
        logging.error(_("Can't create and modify encfs configuration files."))
        logging.error(general_error)
        logging.error(_("Home directory won't be encrypted."))
        return False

    # Move user home dir out of the way
    mount_dir = os.path.join(dest_dir, "home/", username)
    backup_dir = os.path.join(dest_dir, "var/tmp/", username)
    shutil.move(mount_dir, backup_dir)

    # Create necessary dirs, encrypted and mounted(unencrypted)
    encrypted_dir = os.path.join(dest_dir, "home/.encfs/", username)
    os.makedirs(encrypted_dir)
    os.makedirs(mount_dir)

    # Set owner
    shutil.chown(encrypted_dir, username, "users")
    shutil.chown(mount_dir, username, "users")

    # Create encrypted directory
    try:
        #dd if=/dev/urandom of=~/.sync.key bs=256 count=1

        # TODO: FIX THIS. IT DOES NOT PASS --extpass CORRECTLY
        external_password = "--extpass='/bin/echo \"{0}\"'".format(password)
        subprocess.check_call(['encfs', '-v', encrypted_dir, mount_dir, external_password])
    except subprocess.CalledProcessError as process_error:
        logging.error(process_error)

    # Restore user home files
    src = os.path.join(backup_dir, "*")
    shutil.move(src, mount_dir)
    src = os.path.join(backup_dir, ".[A-Za-z0-9]*")
    shutil.move(src, mounted_dir)

    # Delete home backup
    os.rmdir(backup_dir)


if __name__ == '__main__':
    setup("karasu", "/", "1234")
