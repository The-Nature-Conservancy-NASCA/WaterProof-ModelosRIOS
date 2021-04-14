FROM python:2.7

#ADD environment.yml /tmp/environment.yml

ADD requirements.txt /app/requirements.txt
ADD requirements_before.txt /app/requirements_before.txt
ADD dev_requirements.txt /app/dev_requirements.txt

RUN apt update && apt install -y libpq-dev gdal-bin libgdal-dev



#RUN apt-get update && apt-get install -y build-essential
#RUN apt-get install -y libpq-dev python3-dev
#RUN apt-get install -y libspatialindex-dev python-rtree
#RUN apt-get install -y libopenjp2-7-dev

#RUN conda env create -f /tmp/environment.yml

#RUN echo "source activate $(head -1 /tmp/environment.yml | cut -d' ' -f2)" > ~/.bashrc
#ENV PATH /opt/conda/envs/$(head -1 /tmp/environment.yml | cut -d' ' -f2)/bin:$PATH
#SHELL ["conda", "run", "-n", "RIOS", "/bin/bash", "-c"]

WORKDIR /app

RUN pip install -r requirements_before.txt
RUN pip install -r requirements.txt
RUN pip install -r dev_requirements.txt

COPY . /app

RUN chmod +x api.py

#RUN \
# apk add --no-cache postgresql-libs && \
# apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
# pip install -r requirements.txt --no-cache-dir && \
# apk --purge del .build-deps

EXPOSE 5050

CMD ["python", "api.py"]

#CMD ["conda", "run", "-n", "RIOS", "python", "api.py"]
#ENTRYPOINT ["python", "api.py"]