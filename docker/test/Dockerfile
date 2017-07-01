# Pull base image
FROM shilad/cartograph-base:latest

# Define default command
# Note that EFFECTIVE_TRAVIS_BRANCH is set in Cartograph's .travis.yml
CMD  git clone https://github.com/shilad/cartograph.git /cartograph && \
    cd /cartograph && \
    git checkout ${EFFECTIVE_TRAVIS_BRANCH} && \
    ./bin/unit-test.sh && \
    ./bin/integration-test.sh


