FROM ros:jazzy

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /ws

COPY . src/turtlebot3_factory_nav

RUN apt-get update \
 && rosdep update \
 && rosdep install --from-paths src --ignore-src -r -y \
 && rm -rf /var/lib/apt/lists/*

RUN source /opt/ros/jazzy/setup.bash && colcon build

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "turtlebot3_factory_bringup", "factory_sim.launch.py"]
