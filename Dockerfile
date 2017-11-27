FROM tiangolo/uwsgi-nginx-flask:python3.6

# copy over our app code
COPY . /app
# upgrade pip and install required python packages
RUN pip install /app
ENV FLASK_APP main
RUN flask initdb

# set an environmental variable, MESSAGE,
# which the app will use and display
ENV STATIC_PATH /app/main/static