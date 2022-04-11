from git import Repo, GitCommandError
import os
import sys
import shutil
import subprocess

path = os.path.join(os.getcwd(), 'syntheagecco')
destination = 'build_jar'
jar = 'syntheagecco-all.jar'


def pull_syntheagecco():
    # Git
    try:
        repo = Repo.clone_from(url='https://github.com/itcr-uni-luebeck/Synthea-Gecco.git', to_path=path)
        print('Pulled syntheagecco repository')
    except GitCommandError:
        repo = Repo(path)
        print('Repository already present')
    repo.git.checkout('1.0.5')

    # Maven
    if not os.path.exists(os.path.join(destination, jar)):
        subprocess.Popen(os.path.join(path, 'gradlew.bat') + ' shadowJar', cwd=path).wait()
        if not os.path.exists(destination):
            os.mkdir(destination)
        shutil.move(os.path.join(path, 'build', 'libs', jar), os.path.join(destination, jar))


def run_syntheagecco():
    p_count = sys.argv[1]
    os.system('java -jar {path} -p {p_count} -f -gVersion 1.0.5 -d output'.format(
        path=os.path.join(destination, jar), p_count=p_count))


if __name__ == '__main__':
    pull_syntheagecco()
    run_syntheagecco()
