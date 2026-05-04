#!/bin/bash
set -euo pipefail

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

if git show-ref --verify --quiet refs/remotes/origin/Leap-16.1; then
    target_branch="Leap-16.1"
elif git show-ref --verify --quiet refs/remotes/origin/leap-16.1; then
    target_branch="leap-16.1"
else
    echo "Neither origin/Leap-16.1 nor origin/leap-16.1 exists in $package_name"
    exit 1
fi

git fetch --all
git checkout factory
git pull parent factory
git checkout -B "$target_branch" "origin/$target_branch"
git pull parent "$target_branch"
git checkout -b "161_branch_$datestamp" "$target_branch"

# git merge --no-commit factory
# git merge --allow-unrelated-histories -X theirs -m "Merge branch 'factory' into '$target_branch'" factory
git merge --no-ff --allow-unrelated-histories -X theirs --no-commit factory
git read-tree --reset -u factory
git commit -m "Merge branch 'factory' into '$target_branch'"
git push origin "161_branch_$datestamp"

git-obs pr create \
  --title "Sync with Factory" \
  --description "Update to Factory version" \
  --source-owner "$user_name" \
  --source-repo "$package_name" \
  --source-branch "161_branch_$datestamp" \
  --target-owner pool \
  --target-branch "$target_branch"
