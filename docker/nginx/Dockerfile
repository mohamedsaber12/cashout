FROM nginx:latest
ARG NGINX_ENV=prod
ENV NGINX_ENV=${NGINX_ENV}
RUN rm /etc/nginx/conf.d/default.conf
RUN mkdir /www
# COPY /var/www/ /www/
COPY ./conf.d/${NGINX_ENV}.conf /etc/nginx/conf.d/
