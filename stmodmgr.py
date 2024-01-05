#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess

ST_WORKSHOP_ID = 281990
MOD_ALL = 'all'

def get_args():
	args = argparse.ArgumentParser()
	args.add_argument("operation", help="operation", choices=["install", "uninstall", "upgrade"])
	args.add_argument("mod_id", help="workshop mod id")
	args.add_argument("-d", "--install-dir", help="workshop installation directory", default=f"{os.environ['HOME']}/.local/share/stmodloader")
	args.add_argument("-s", "--stellaris-dir", help="stellaris mod directorty", default=f"{os.environ['HOME']}/.local/share/Paradox Interactive/Stellaris/mod")
	# TODO modlist from file
	args.add_help = True
	args.description = ("Use 'all' instead of a mod_id to operate on every installed mod. Only works with 'upgrade' and 'uninstall'.")
	args = args.parse_args()
	args.mod_id = args.mod_id.lower()
	if args.mod_id == "all":
		if args.operation == "install":
			print("cannot use 'all' with operation 'install'")
			exit(1)
	elif not args.mod_id.isnumeric():
		print("invalid argument 'mod_id")
	return args

def run_steamcmd(install_dir: str, command: str):
	proc = subprocess.run(["steamcmd", f"+force_install_dir {install_dir} +login anonymous {command} +quit"])
	# steamcmd does print a final newline
	print("")
	if proc.returncode != 0:
		raise RuntimeError("steamcmd failed")

def remove(path: str):
	try:
		if os.path.islink(path):
			os.unlink(path)
		elif os.path.isdir(path):
			shutil.rmtree(path)
		else:
			os.remove(path)
	except Exception as e:
		print(e)
		print(f"failed to remove file '{path}'")
		exit(1)
	
def get_mod_ids(path: str):
	is_mod_descriptor = lambda f : not not re.match("steam_\d+\.mod$", f)
	get_mod_id = lambda f : re.search("\d+", f).group()
	return list(map(get_mod_id, filter(is_mod_descriptor, os.listdir(path))))

def install(args):
	print(f"installing mod {args.mod_id}")

	if not os.path.exists(args.install_dir):
		os.mkdir(args.install_dir)

	try:
		run_steamcmd(args.install_dir, f"+workshop_download_item {ST_WORKSHOP_ID} {args.mod_id}")
	except RuntimeError:
		print("download failed, aborting")
		exit(1)
	print(f"downloaded mod {args.mod_id}")

	mod_dir = f"{args.install_dir}/steamapps/workshop/content/{ST_WORKSHOP_ID}/{args.mod_id}"
	symlink = f"{args.stellaris_dir}/steam_{args.mod_id}"

	mod_descriptor = None
	mod_path = f"mod/steam_{args.mod_id}"
	try:
		with open(f"{mod_dir}/descriptor.mod", "r") as f:
			mod_descriptor = f.read()
	except Exception as e:
		print(e)
		print(f"failed to read file '{mod_dir}/descriptor.mod'")
		exit(1)
	if not re.search("path=", mod_descriptor, flags=re.MULTILINE):
		mod_descriptor += f"\n'path={mod_path}'"
	else:
		# TODO verify this
		mod_descriptor = re.sub("path=.+", f'path="{mod_path}"', mod_descriptor, flags=re.MULTILINE)

	print(f"writing mod descriptor file")
	try:
		with open(f"{args.stellaris_dir}/steam_{args.mod_id}.mod", "w") as f:
			f.write(mod_descriptor)
	except Exception as e:
		print(e)
		print(f"failed to write mod descriptor file '{symlink}'")
		exit(1)
		
	if os.path.exists(symlink):
		remove(symlink)

	print(f"creating symlink '{symlink}'")
	os.symlink(mod_dir, symlink, target_is_directory=True)
	print(f"installed mod {args.mod_id}")

def upgrade(args):
	if args.mod_id == MOD_ALL:
		print("updating all mods")
		mods = get_mod_ids(args.stellaris_dir)
	else:
		print(f"updating mod {args.mod_id}")
		mods = [args.mod_id]

	cmd = []
	for mod in mods:
		cmd.append(f"+workshop_download_item {ST_WORKSHOP_ID} {mod}")
	cmd = " ".join(cmd)
	run_steamcmd(args.install_dir, cmd)

def uninstall(args):
	if not os.path.exists(args.stellaris_dir):
		print(f"stellaris mod directory '{args.stellaris_dir}' not found, aborting")
		exit(1)
	
	mods = args.mod_id == MOD_ALL and get_mod_ids(args.stellaris_dir) or [args.mod_id]

	for mod in mods:
		print(f"uninstalling mod {mod}")

		symlink = f"{args.stellaris_dir}/steam_{mod}"
		if os.path.exists(symlink):
			print(f"removing symlink '{symlink}'")
			remove(symlink)
		mod_descriptor = f"{symlink}.mod"
		if os.path.exists(mod_descriptor):
			print(f"removing mod descriptor file '{mod_descriptor}'")
			remove(mod_descriptor)
		
		print(f"uninstalled mod {mod}")

def main():
	args = get_args()
	match args.operation:
		case "install":
			install(args)
		case "uninstall":
			uninstall(args)
		case "upgrade":
			upgrade(args)
	print("done")

main()