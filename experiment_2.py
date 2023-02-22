import re
url = 'www.google.com'
package='hello.deb'
version = '5.15.0.9_lts-bullpen'

with open('./installer/base_installer', 'rt') as f:
    commands = f.read()
commands = re.sub('SUBSTITUTE_URL', url, commands)
print(commands)
# commands.replace('SUBSTITUTE_URL', url)
# commands.replace('SUBSTITUTE_PACKAGE', package)
# commands.replace('SUBSTITUTE_VERSION', version)

# with open( f'./installer/installer_trial', 'wt') as f:
#     f.write(commands)