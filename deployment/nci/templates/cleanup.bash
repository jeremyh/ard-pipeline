chmod u+w {{ target_modules_repo }}/modulefiles/ard-pipeline/{{ target_version }}
rm -rf {{ target_modules_repo }}/modulefiles/ard-pipeline/{{ target_version }}
chmod -R u+w {{ target_modules_repo }}/ard-pipeline/{{ target_version }}
rm -rf {{ target_modules_repo }}/ard-pipeline/{{ target_version }}
rm -rf ./build
