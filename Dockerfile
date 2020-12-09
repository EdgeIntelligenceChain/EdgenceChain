# set base image (host OS)
FROM python:3.6.7

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY / .

# Make port 9999 available to the world outside this container
EXPOSE 9999

# entrypoint for this app
ENTRYPOINT ["python"]

# parameter to run on container start
CMD ["main.py"]
