DROP TABLE IF EXISTS `room_member`;

DROP TABLE IF EXISTS `room`;

DROP TABLE IF EXISTS `user`;

CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `token` varchar(255) NOT NULL,
  `leader_card_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

CREATE TABLE `room` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `live_id` int NOT NULL,
  `owner_id` bigint NOT NULL,
  `wait_room_status` tinyint NOT NULL,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`owner_id`) REFERENCES `user` (`id`),
  INDEX `wait_room_status_live_id` (`wait_room_status`, `live_id`)
);

CREATE TABLE `room_member`(
  `room_id` bigint NOT NULL,
  `member_id` bigint NOT NULL,
  `live_difficulty` tinyint NOT NULL,
  `judge_count_list` varchar(50) DEFAULT NULL,
  `score` int DEFAULT NULL,
  PRIMARY KEY (`room_id`, `member_id`),
  FOREIGN KEY (`room_id`) REFERENCES `room` (`id`),
  FOREIGN KEY (`member_id`) REFERENCES `user` (`id`)
);