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

# We need git!
RUN apt-get --assume-yes install git

# Bindings for leveldb
RUN apt-get install -y libleveldb-dev

#Install python requirements
# Numpy and Cython must be first for weird reasons.
RUN pip install --upgrade pip
RUN pip install numpy Cython
COPY requirements.txt .
RUN pip install -r ../../requirements.txt

