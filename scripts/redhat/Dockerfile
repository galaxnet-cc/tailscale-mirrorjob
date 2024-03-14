FROM dokken/centos-8

# Update and install dnf plugins, createrepo_c, and python3 in one step to minimize the number of layers
RUN sed -i 's/mirrorlist/#mirrorlist/g' /etc/yum.repos.d/CentOS-*
RUN sed -i 's|#baseurl=http://mirror.centos.org|baseurl=http://vault.centos.org|g' /etc/yum.repos.d/CentOS-* 
RUN yum -y install dnf && dnf -y install 'dnf-command(reposync)' createrepo_c && yum -y install python3

# Copy the yum-sync script to the container
COPY ./yum-sync.py /usr/local/bin/
RUN pip3 install requests

# Set the default command
CMD ["/usr/lib/systemd/systemd"]
