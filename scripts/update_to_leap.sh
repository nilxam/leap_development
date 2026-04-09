#!/bin/bash

if [ "$#" -ne 1 ]; then
        echo "Usage: $0 <package_name>"
        exit 1
fi

package_name="$1"

datestamp=$(date +"%Y%m%d")

git-obs repo fork pool/$package_name
git-obs repo clone mlin7442/$package_name
cd $package_name
git checkout -b 161_branch_$datestamp origin/leap-16.1
# git merge --no-commit factory
# git merge --allow-unrelated-histories -X theirs -m "Merge branch 'factory' into 'leap-16.1'" factory
git merge --no-ff --allow-unrelated-histories -X theirs --no-commit factory
git read-tree --reset -u factory
git commit -m "Merge branch 'factory' into 'leap-16.1'"
git push origin 161_branch_$datestamp
git-obs pr create --title "Update to Factory version" --description "Update to Factory version" --source-owner mlin7442 --source-repo $package_name --source-branch 161_branch_$datestamp --target-owner pool --target-branch leap-16.1
