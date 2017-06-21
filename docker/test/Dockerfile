#Pull base image
FROM shilad/cartograph-base:latest

# Checkout cartograph and clone to appropriate path
WORKDIR /home
RUN git clone https://github.com/shilad/cartograph.git ./cartograph
WORKDIR /home/cartograph
RUN git checkout integration-test

#Define default command
CMD  git pull && \
    ./bin/docker-integration-test.sh


