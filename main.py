import os
import shutil
import subprocess
import re


def find_files(filename, search_path):
    for root, _, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)
    return None


def replace_release_2(build_gradle, release_file):
    rep = ["release{",
           "tagTemplate = 'v${version}'",
           "pushReleaseVersionBranch = 'master'",
           "failOnUnversionedFiles = false",
           "failOnCommitNeeded = false",
           "git {",
           "     requireBranch = 'develop'",
           "     pushToRemote = 'origin'",
           "}",
           "}"]
    rep = [i + '\n' for i in rep]
    f = open(build_gradle, 'r')
    file_lines = f.readlines()
    n = len(file_lines)
    start = -1
    end = -1
    i = 0
    stack = ['{']
    while i < n:
        line = file_lines[i].rstrip().lstrip().replace(' ', '').replace('\n', '').replace('\t', '').replace('\r', '')
        if end != -1:
            break
        if start != -1:
            for j in line:
                if j == '{':
                    stack.append('{')
                elif j == '}':
                    stack.pop(-1)
                    if len(stack) == 0:
                        end = i
                        break

        elif line == "release{" or (line == "release" and file_lines[i + 1].lstrip()[0] == '{'):
            start = i
            if line != "release{":
                file_lines[i + 1] = file_lines[i + 1].lstrip()[1:]
        i += 1
    new_file_lines = []
    if start == -1 or end == -1:
        new_file_lines = file_lines + rep
    else:
        new_file_lines = file_lines[:start] + file_lines[end + 1:] + rep
    print(start, end)
    final_lines = []
    for line in new_file_lines:
        if "net.researchgate" in line:
            l = re.sub(r'\b2\.\w*\.\w*', '2.8.0', line)
            final_lines.append(l)
        else:
            final_lines.append(line)

    with open(build_gradle, 'w') as file:
        file.writelines(final_lines)


# def replace_release(build_gradle, release_file):
#     rep = '''release{
#        tagTemplate = 'v${version}'
#        pushReleaseVersionBranch = 'master'
#        failOnUnversionedFiles = false
#        failOnCommitNeeded = false
#        git {
#             requireBranch = 'develop'
#             pushToRemote = 'origin'
#         }
#     }'''
#
#     file = open(release_file, 'r')
#     release_string = file.read()
#     file.close()
#
#     res1 = ""
#     with open(build_gradle, 'r') as file:
#         filedata = file.read()
#         # Replace the target string
#         print(filedata.find(release_string))
#         # print(release_string)
#         res1 = filedata.replace(release_string, rep)
#     # Write the file out again
#     with open(build_gradle, 'w') as file:
#         file.write(res1)


def execute():
    base_path = '/home/eshapriyadarshi/projects/repos/vm'
    ais_db = '/home/eshapriyadarshi/projects/repos/ais/ais-db'
    release_file = '/home/eshapriyadarshi/release.txt'
    gradle_build = 'build.gradle'
    jenkins_file = 'JenkinsfileRelease'
    ais_adaptor_jenkins = '/home/eshapriyadarshi/projects/repos/ais/ais-adaptor/JenkinsfileRelease'
    failed_repos = []
    with open('/home/eshapriyadarshi/sites.txt') as repo_file:
        repos = [line.rstrip() for line in repo_file]
        for repo in repos:
            repo_folder = repo.split('/')[-1].split('.')[0]
            try:
                repo_directory = os.path.join(base_path, repo_folder)
                if os.path.isdir(repo_directory) and repo_directory != base_path:
                    shutil.rmtree(repo_directory)

                # Construct the git clone command
                command = ["git", "clone", repo]
                # Use Popen to run the command and communicate with the subprocess
                p = subprocess.Popen(command, cwd=base_path, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                print(stdout.decode())
                print(stderr.decode())

                os.chdir(repo_directory)
                checkout_master = ["git", "checkout", "master"]
                p = subprocess.Popen(checkout_master, cwd=repo_directory, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                print(stdout.decode())
                print(stderr.decode())

                file_path = os.path.join(os.getcwd(), jenkins_file)
                # copy from ais-adaptor
                shutil.copy(ais_adaptor_jenkins, file_path)
                print('copied JenkinsFile')

                # get build.gradle
                build_gradle = find_files(gradle_build, os.getcwd())
                replace_release_2(build_gradle, release_file)
                print('Updated build.gradle')

                #add updated files
                subprocess.run(["git", "add", jenkins_file])
                subprocess.run(["git", "add", build_gradle])
                print('git add done')

                # git commit and push
                subprocess.run(["git", "commit", "-m", "[ICT-1064] - made jenkins related changes"])
                print('git commit done')
                subprocess.run(["git", "push"])
                print('git push done')

                # Get the latest commit hash from the git log
                latest_commit_hash = subprocess.check_output(["git", "rev-parse", "master"])
                # Decode the byte string to a string
                latest_commit_hash = latest_commit_hash.decode("utf-8").strip()
                print(f"The latest commit hash is: {latest_commit_hash}")

                # checkout to develop
                subprocess.run(["git", "checkout", "develop"])
                print('checkout to develop')
                # cherry pick the commit in develop
                subprocess.run(["git", "cherry-pick", latest_commit_hash])
                subprocess.run(["git", "mergetool"])
                print("cherry-pick done")
                subprocess.run(["git", "mergetool"])
                subprocess.run(["git", "cherry-pick", "--continue"])
                subprocess.run(["git", "push"])
                print('git push done in develop')
            except subprocess.CalledProcessError:
                print("cherry-pick error")
            except Exception as e:
                failed_repos.append(repo)
                print("++++++" + repo + "++++++")
                print(e.__str__())
    for i in failed_repos:
        print(i)


if __name__ == '__main__':
    execute()
