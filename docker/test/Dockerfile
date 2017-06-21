#Pull base image
FROM ubuntu

RUN \
  apt-get update


#Install python
RUN apt-get install -y python2.7

#Install pip
RUN apt-get install -y python-pip

#Install libgeos-dev
RUN apt-get install -y libgeos-dev

#Install libatlas-base-dev
RUN apt-get install -y libatlas-base-dev

#Install libffi-dev
RUN apt-get install libffi-dev

#Install libssl-dev
RUN apt-get install -y libssl-dev

#Install qt
RUN apt-get install -y qt4-default

#Install cmake
RUN apt-get install -y cmake

#Install cairo
RUN apt-get install -y libcairo2-dev

#Install python requirements
RUN pip install numpy Cython   # Numpy and Cython must be first for weird reasons.
COPY requirements.txt .
RUN pip install -r ../../requirements.txt

# Checkout cartograph and clone to appropriate path
RUN apt-get --assume-yes install git
WORKDIR /home
RUN git clone https://github.com/shilad/cartograph.git ./cartograph
WORKDIR /home/cartograph
RUN git checkout integration-test

#Define default command
CMD  git pull && \
    ./docker/test/run-docker-tests.sh


