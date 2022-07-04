from git import Repo, GitCommandError
import os
import sys
import shutil
import subprocess

# path = os.path.join(os.getcwd(), 'syntheagecco')
destination = 'build_jar'
# jar = 'syntheagecco-all.jar'


def pull(url, branch, path, jar_name):
    # Git
    try:
        repo = Repo.clone_from(url=url, to_path=path)
        print('Pulled repository @ {url}'.format(url=url))
    except GitCommandError:
        repo = Repo(path)
        print('Repository already present')
    repo.git.checkout(branch)

    # Build JAR
    if not os.path.exists(os.path.join(destination, jar_name)):
        subprocess.Popen(os.path.join(path, 'gradlew.bat') + ' shadowJar', cwd=path).wait()
        if not os.path.exists(destination):
            os.mkdir(destination)
        shutil.move(os.path.join(path, 'build', 'libs', jar_name), os.path.join(destination, jar_name))


def run_syntheagecco(jar_name):
    p_count = sys.argv[2]
    os.system('java -jar {path} -p {p_count} -f -gVersion 1.0.5 -d output'.format(
        path=os.path.join(destination, jar_name), p_count=p_count))


def run_syntheakds(jar_name):
    p_count = sys.argv[2]
    os.system('java -jar {path} {p_count}'.format(
        path=os.path.join(destination, jar_name), p_count=p_count))


if __name__ == '__main__':
    program = sys.argv[1]
    if program == "syntheagecco":
        path = os.path.join(os.getcwd(), 'syntheagecco')
        pull(url='https://github.com/itcr-uni-luebeck/Synthea-Gecco.git', branch='1.0.5', path=path,
             jar_name='syntheagecco-all.jar')
        run_syntheagecco(jar_name='syntheagecco-all.jar')
    else:
        path = os.path.join(os.getcwd(), 'syntheakds')
        pull(url='https://github.com/itcr-uni-luebeck/Synthea-MII-KDS.git', branch='main', path=path,
             jar_name='syntheakds-all.jar')
        run_syntheakds(jar_name='syntheakds-all.jar')
