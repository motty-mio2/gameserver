DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `leader_card_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

DROP TABLE IF EXISTS `room`;
CREATE TABLE `room` (
  `room_id` bigint NOT NULL AUTO_INCREMENT,
  `live_id` varchar(255) DEFAULT NULL,
  `room_members_count` int DEFAULT NULL,
  `max_user_count` int DEFAULT 4,
  `owner_id` bigint DEFAULT NULL,
  `status` int DEFAULT 1,
  PRIMARY KEY (`room_id`)
);

DROP TABLE IF EXISTS `room_member`;
CREATE TABLE `room_member` (
  `room_id` bigint NOT NULL,
  `live_id` varchar(255) DEFAULT NULL,
  `id` bigint DEFAULT NULL,
  `exist` int DEFAULT 1,
  PRIMARY KEY (`room_id`)
);