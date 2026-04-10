#!/bin/bash

if [ "$#" -ne 2 ]; then
        echo "Usage: $0 <username> <package_name>"
        exit 1
fi

user_name="$1"
package_name="$2"

datestamp=$(date +"%Y%m%d")

git-obs repo fork pool/$package_name
git-obs repo clone $user_name/$package_name
cd $package_name
git checkout leap-16.1
git pull parent leap-16.1
git checkout -b 161_branch_$datestamp leap-16.1
# git merge --no-commit factory
# git merge --allow-unrelated-histories -X theirs -m "Merge branch 'factory' into 'leap-16.1'" factory
git merge --no-ff --allow-unrelated-histories -X theirs --no-commit factory
git read-tree --reset -u factory
git commit -m "Merge branch 'factory' into 'leap-16.1'"
git push origin 161_branch_$datestamp
git-obs pr create --title "Update to Factory version" --description "Update to Factory version" --source-owner $user_name --source-repo $package_name --source-branch 161_branch_$datestamp --target-owner pool --target-branch leap-16.1
