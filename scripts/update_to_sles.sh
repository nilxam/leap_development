#!/bin/bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
        echo "Usage: $0 <username> <package_name>"
        exit 1
fi

user_name="$1"
package_name="$2"

datestamp=$(date +"%Y%m%d")

OBS_LOGIN="ibs"
# Switch this to slfo-x.y after RC
BRANCH="slfo-main"

git-obs -G "${OBS_LOGIN}" repo fork "pool/$package_name"
git-obs -G "${OBS_LOGIN}" repo clone "$user_name/$package_name"

cd "$package_name"
git checkout "${BRANCH}"
git pull parent "${BRANCH}"
git fetch origin factory
git checkout -b "${BRANCH}_branch_$datestamp" "${BRANCH}"

git merge --no-ff --allow-unrelated-histories -X theirs --no-commit origin/factory
git read-tree --reset -u origin/factory
git commit -m "Merge branch 'factory' into '${BRANCH}'"

git push origin "${BRANCH}_branch_$datestamp"
exit

# skip PR
git-obs -G "${OBS_LOGIN}" pr create \
  --title "Update to Factory version" \
  --description "Update to Factory version" \
  --source-owner "$user_name" \
  --source-repo "$package_name" \
  --source-branch "${BRANCH}_branch_$datestamp" \
  --target-owner pool \
  --target-branch "${BRANCH}"
