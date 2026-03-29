/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `zweig_trackbacks`
--

DROP TABLE IF EXISTS `zweig_trackbacks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_trackbacks` (
  `tb_id` int(11) NOT NULL AUTO_INCREMENT,
  `tb_page` int(11) DEFAULT NULL,
  `tb_title` varbinary(255) NOT NULL,
  `tb_url` blob NOT NULL,
  `tb_ex` blob,
  `tb_name` varbinary(255) DEFAULT NULL,
  PRIMARY KEY (`tb_id`),
  KEY `tb_page` (`tb_page`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_trackbacks`
--

LOCK TABLES `zweig_trackbacks` WRITE;
/*!40000 ALTER TABLE `zweig_trackbacks` DISABLE KEYS */;
/*!40000 ALTER TABLE `zweig_trackbacks` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_updatelog`
--

DROP TABLE IF EXISTS `zweig_updatelog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_updatelog` (
  `ul_key` varbinary(255) NOT NULL,
  `ul_value` blob,
  PRIMARY KEY (`ul_key`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_updatelog`
--

LOCK TABLES `zweig_updatelog` WRITE;
/*!40000 ALTER TABLE `zweig_updatelog` DISABLE KEYS */;
INSERT INTO `zweig_updatelog` VALUES (_binary 'AddRFCAndPMIDInterwiki',NULL),(_binary 'AddRFCandPMIDInterwiki',NULL),(_binary 'DeduplicateArchiveRevId',NULL),(_binary 'DeleteDefaultMessages',NULL),(_binary 'FixDefaultJsonContentPages',NULL),(_binary 'MigrateActors',NULL),(_binary 'MigrateArchiveText',NULL),(_binary 'MigrateComments',NULL),(_binary 'MigrateImageCommentTemp',NULL),(_binary 'PopulateArchiveRevId',NULL),(_binary 'PopulateChangeTagDef',NULL),(_binary 'PopulateContentTables',NULL),(_binary 'RefreshExternallinksIndex v1+IDN',NULL),(_binary 'actor-actor_name-patch-actor-actor_name-varbinary.sql',NULL),(_binary 'cl_fields_update',NULL),(_binary 'cleanup empty categories',NULL),(_binary 'convert transcache field',NULL),(_binary 'externallinks-el_index_60-patch-externallinks-el_index_60-drop-default.sql',NULL),(_binary 'filearchive-fa_major_mime-patch-fa_major_mime-chemical.sql',NULL),(_binary 'fix protocol-relative URLs in externallinks',NULL),(_binary 'image-img_description-patch-image-img_description-default.sql',NULL),(_binary 'image-img_major_mime-patch-img_major_mime-chemical.sql',NULL),(_binary 'image-img_media_type-patch-add-3d.sql',NULL),(_binary 'iwlinks-iwl_prefix-patch-extend-iwlinks-iwl_prefix.sql',NULL),(_binary 'job-patch-job-params-mediumblob.sql',NULL),(_binary 'mime_minor_length',NULL),(_binary 'oldimage-oi_major_mime-patch-oi_major_mime-chemical.sql',NULL),(_binary 'page-page_restrictions-patch-page_restrictions-null.sql',NULL),(_binary 'populate *_from_namespace',NULL),(_binary 'populate category',NULL),(_binary 'populate externallinks.el_index_60',NULL),(_binary 'populate fa_sha1',NULL),(_binary 'populate img_sha1',NULL),(_binary 'populate ip_changes',NULL),(_binary 'populate log_search',NULL),(_binary 'populate log_usertext',NULL),(_binary 'populate pp_sortkey',NULL),(_binary 'populate rev_len and ar_len',NULL),(_binary 'populate rev_parent_id',NULL),(_binary 'populate rev_sha1',NULL),(_binary 'recentchanges-rc_ip-patch-rc_ip_modify.sql',NULL),(_binary 'revision-rev_comment-patch-revision-rev_comment-default.sql',NULL),(_binary 'revision-rev_text_id-patch-rev_text_id-default.sql',NULL),(_binary 'site_stats-patch-site_stats-modify.sql',NULL),(_binary 'sites-site_global_key-patch-sites-site_global_key.sql',NULL),(_binary 'user_former_groups-ufg_group-patch-ufg_group-length-increase-255.sql',NULL),(_binary 'user_groups-ug_group-patch-ug_group-length-increase-255.sql',NULL),(_binary 'user_properties-up_property-patch-up_property.sql',NULL);
/*!40000 ALTER TABLE `zweig_updatelog` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_uploadstash`
--

DROP TABLE IF EXISTS `zweig_uploadstash`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_uploadstash` (
  `us_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `us_user` int(10) unsigned NOT NULL,
  `us_key` varbinary(255) NOT NULL,
  `us_orig_path` varbinary(255) NOT NULL,
  `us_path` varbinary(255) NOT NULL,
  `us_source_type` varbinary(50) DEFAULT NULL,
  `us_timestamp` varbinary(14) NOT NULL,
  `us_status` varbinary(50) NOT NULL,
  `us_size` int(10) unsigned NOT NULL,
  `us_sha1` varbinary(31) NOT NULL,
  `us_mime` varbinary(255) DEFAULT NULL,
  `us_media_type` enum('UNKNOWN','BITMAP','DRAWING','AUDIO','VIDEO','MULTIMEDIA','OFFICE','TEXT','EXECUTABLE','ARCHIVE','3D') DEFAULT NULL,
  `us_image_width` int(10) unsigned DEFAULT NULL,
  `us_image_height` int(10) unsigned DEFAULT NULL,
  `us_image_bits` smallint(5) unsigned DEFAULT NULL,
  `us_chunk_inx` int(10) unsigned DEFAULT NULL,
  `us_props` blob,
  PRIMARY KEY (`us_id`),
  UNIQUE KEY `us_key` (`us_key`),
  KEY `us_user` (`us_user`),
  KEY `us_timestamp` (`us_timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_uploadstash`
--

LOCK TABLES `zweig_uploadstash` WRITE;
/*!40000 ALTER TABLE `zweig_uploadstash` DISABLE KEYS */;
/*!40000 ALTER TABLE `zweig_uploadstash` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_user`
--

DROP TABLE IF EXISTS `zweig_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_user` (
  `user_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_name` varbinary(255) NOT NULL DEFAULT '',
  `user_real_name` varbinary(255) NOT NULL DEFAULT '',
  `user_password` tinyblob NOT NULL,
  `user_newpassword` tinyblob NOT NULL,
  `user_newpass_time` binary(14) DEFAULT NULL,
  `user_email` tinyblob NOT NULL,
  `user_touched` binary(14) NOT NULL DEFAULT '\0\0\0\0\0\0\0\0\0\0\0\0\0\0',
  `user_token` binary(32) NOT NULL DEFAULT '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0',
  `user_email_authenticated` binary(14) DEFAULT NULL,
  `user_email_token` binary(32) DEFAULT NULL,
  `user_email_token_expires` binary(14) DEFAULT NULL,
  `user_registration` binary(14) DEFAULT NULL,
  `user_editcount` int(11) DEFAULT NULL,
  `user_password_expires` varbinary(14) DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`),
  KEY `user_email_token` (`user_email_token`),
  KEY `user_email` (`user_email`(50))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_user`
--

LOCK TABLES `zweig_user` WRITE;
/*!40000 ALTER TABLE `zweig_user` DISABLE KEYS */;
INSERT INTO `zweig_user` VALUES (1,_binary 'Sysop','',_binary ':B:7109fc98:325e5fa3526296cdb7e326e5d8e187d1','',NULL,'',_binary '20081126204110',_binary 'cdd7b92436a00ef7ac013756342b8750',NULL,_binary '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0',NULL,_binary '20081114205140',51,NULL),(2,_binary 'Klawiter',_binary 'Randolph Klawiter',_binary ':pbkdf2:sha512:30000:64:gQvzUZCb9RReWgSoWVneWw==:gzx/mTEH/84fxqVx0Yy7RlMqFCWHMlDBBrRov6a3Gg0cRm7V1etexRSNnG5SR7W7i5jImEW18dHACevU2pXNLA==','',NULL,_binary 'klawiter.1@nd,edu',_binary '20210827174834',_binary '5ef277aa444c089a82a1c2bb5553b70d',NULL,_binary '3c0535d8208b39e0eb5cc0b4d8f7c83e',_binary '20090415174116',_binary '20081114205632',56048,NULL),(3,_binary 'DKlawiter',_binary 'David Klawiter',_binary ':pbkdf2:sha512:30000:64:pUUTIM7YJjV8Q3LrvML68w==:Rx/Bzaa7RPWPkN/AT+YxZdhMBeMDET2b3M27Ln8BePD1FQKI3SxNW8u33Cja8zJ4LnhtXB/JI+jhyKaBv/+C+A==','',NULL,'',_binary '20210827175230',_binary '59becfa75ca79ccfdbb215f2a611da98',NULL,_binary '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0',NULL,_binary '20081126204451',3008,NULL),(4,_binary 'Redirect fixer','','','',_binary '20100225215929','',_binary '20210131200534',_binary '6f5824026385f5f4c801644f2b34bb5b',NULL,NULL,NULL,_binary '20100225215929',896,NULL);
/*!40000 ALTER TABLE `zweig_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_user_former_groups`
--

DROP TABLE IF EXISTS `zweig_user_former_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_user_former_groups` (
  `ufg_user` int(10) unsigned NOT NULL DEFAULT '0',
  `ufg_group` varbinary(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`ufg_user`,`ufg_group`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_user_former_groups`
--

LOCK TABLES `zweig_user_former_groups` WRITE;
/*!40000 ALTER TABLE `zweig_user_former_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `zweig_user_former_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_user_groups`
--

DROP TABLE IF EXISTS `zweig_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_user_groups` (
  `ug_user` int(10) unsigned NOT NULL DEFAULT '0',
  `ug_group` varbinary(255) NOT NULL DEFAULT '',
  `ug_expiry` varbinary(14) DEFAULT NULL,
  PRIMARY KEY (`ug_user`,`ug_group`),
  KEY `ug_group` (`ug_group`),
  KEY `ug_expiry` (`ug_expiry`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_user_groups`
--

LOCK TABLES `zweig_user_groups` WRITE;
/*!40000 ALTER TABLE `zweig_user_groups` DISABLE KEYS */;
INSERT INTO `zweig_user_groups` VALUES (1,_binary 'bureaucrat',NULL),(1,_binary 'sysop',NULL),(3,_binary 'bureaucrat',NULL),(3,_binary 'sysop',NULL);
/*!40000 ALTER TABLE `zweig_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_user_newtalk`
--

DROP TABLE IF EXISTS `zweig_user_newtalk`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_user_newtalk` (
  `user_id` int(10) unsigned NOT NULL DEFAULT '0',
  `user_ip` varbinary(40) NOT NULL DEFAULT '',
  `user_last_timestamp` varbinary(14) DEFAULT NULL,
  KEY `un_user_id` (`user_id`),
  KEY `un_user_ip` (`user_ip`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_user_newtalk`
--

LOCK TABLES `zweig_user_newtalk` WRITE;
/*!40000 ALTER TABLE `zweig_user_newtalk` DISABLE KEYS */;
/*!40000 ALTER TABLE `zweig_user_newtalk` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_user_properties`
--

DROP TABLE IF EXISTS `zweig_user_properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_user_properties` (
  `up_user` int(10) unsigned NOT NULL,
  `up_property` varbinary(255) NOT NULL,
  `up_value` blob,
  PRIMARY KEY (`up_user`,`up_property`),
  KEY `user_properties_property` (`up_property`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_user_properties`
--

LOCK TABLES `zweig_user_properties` WRITE;
/*!40000 ALTER TABLE `zweig_user_properties` DISABLE KEYS */;
INSERT INTO `zweig_user_properties` VALUES (1,_binary 'ajaxsearch',_binary '0'),(1,_binary 'contextchars',_binary '50'),(1,_binary 'contextlines',_binary '5'),(1,_binary 'disablesuggest',_binary '0'),(1,_binary 'editsection',_binary '1'),(1,_binary 'editwidth',_binary '0'),(1,_binary 'enotifwatchlistpages',_binary '0'),(1,_binary 'extendwatchlist',_binary '0'),(1,_binary 'externaldiff',_binary '0'),(1,_binary 'externaleditor',_binary '0'),(1,_binary 'highlightbroken',_binary '1'),(1,_binary 'quickbar',_binary '1'),(1,_binary 'rememberpassword',_binary '0'),(1,_binary 'searchlimit',_binary '20'),(1,_binary 'showjumplinks',_binary '1'),(1,_binary 'showtoc',_binary '1'),(1,_binary 'skin',''),(1,_binary 'thumbsize',_binary '2'),(1,_binary 'usenewrc',_binary '0'),(1,_binary 'watchcreations',_binary '0'),(1,_binary 'watchdefault',_binary '0'),(2,_binary 'ajaxsearch',''),(2,_binary 'contextchars',_binary '50'),(2,_binary 'contextlines',_binary '5'),(2,_binary 'disablesuggest',''),(2,_binary 'editsection',_binary '1'),(2,_binary 'editwidth',_binary '0'),(2,_binary 'enotifwatchlistpages',_binary '0'),(2,_binary 'extendwatchlist',_binary '0'),(2,_binary 'externaldiff',_binary '0'),(2,_binary 'externaleditor',_binary '0'),(2,_binary 'highlightbroken',_binary '1'),(2,_binary 'justify',_binary '0'),(2,_binary 'nocache',_binary '0'),(2,_binary 'quickbar',_binary '1'),(2,_binary 'rememberpassword',_binary '0'),(2,_binary 'searchNs1',_binary '0'),(2,_binary 'searchNs10',_binary '0'),(2,_binary 'searchNs11',_binary '0'),(2,_binary 'searchNs12',_binary '0'),(2,_binary 'searchNs13',_binary '0'),(2,_binary 'searchNs14',_binary '0'),(2,_binary 'searchNs15',_binary '0'),(2,_binary 'searchNs2',_binary '0'),(2,_binary 'searchNs3',_binary '0'),(2,_binary 'searchNs4',_binary '0'),(2,_binary 'searchNs5',_binary '0'),(2,_binary 'searchNs6',_binary '0'),(2,_binary 'searchNs7',_binary '0'),(2,_binary 'searchNs8',_binary '0'),(2,_binary 'searchNs9',_binary '0'),(2,_binary 'searchlimit',_binary '20'),(2,_binary 'showjumplinks',_binary '1'),(2,_binary 'shownumberswatching',_binary '0'),(2,_binary 'showtoc',_binary '1'),(2,_binary 'skin',_binary 'monobook'),(2,_binary 'thumbsize',_binary '2'),(2,_binary 'timecorrection',''),(2,_binary 'usenewrc',_binary '0'),(2,_binary 'variant',''),(2,_binary 'watchcreations',_binary '0'),(2,_binary 'watchdefault',_binary '0'),(3,_binary 'extendwatchlist',_binary '0'),(3,_binary 'rclimit',_binary '100'),(3,_binary 'searchNs1',_binary '0'),(3,_binary 'searchNs10',_binary '0'),(3,_binary 'searchNs11',_binary '0'),(3,_binary 'searchNs12',_binary '0'),(3,_binary 'searchNs13',_binary '0'),(3,_binary 'searchNs14',_binary '0'),(3,_binary 'searchNs15',_binary '0'),(3,_binary 'searchNs2',_binary '0'),(3,_binary 'searchNs3',_binary '0'),(3,_binary 'searchNs4',_binary '0'),(3,_binary 'searchNs5',_binary '0'),(3,_binary 'searchNs6',_binary '0'),(3,_binary 'searchNs7',_binary '0'),(3,_binary 'searchNs8',_binary '0'),(3,_binary 'searchNs9',_binary '0'),(3,_binary 'thumbsize',_binary '2'),(3,_binary 'timecorrection',_binary 'Offset|-240'),(3,_binary 'usenewrc',_binary '0'),(3,_binary 'watchcreations',_binary '0'),(3,_binary 'watchdefault',_binary '0'),(4,_binary 'ajaxsearch',_binary '0'),(4,_binary 'contextchars',_binary '50'),(4,_binary 'contextlines',_binary '5'),(4,_binary 'disablesuggest',_binary '0'),(4,_binary 'editsection',_binary '1'),(4,_binary 'editwidth',_binary '0'),(4,_binary 'enotifwatchlistpages',_binary '0'),(4,_binary 'extendwatchlist',_binary '0'),(4,_binary 'externaldiff',_binary '0'),(4,_binary 'externaleditor',_binary '0'),(4,_binary 'highlightbroken',_binary '1'),(4,_binary 'quickbar',_binary '1'),(4,_binary 'rememberpassword',_binary '0'),(4,_binary 'searchlimit',_binary '20'),(4,_binary 'showjumplinks',_binary '1'),(4,_binary 'showtoc',_binary '1'),(4,_binary 'skin',''),(4,_binary 'thumbsize',_binary '2'),(4,_binary 'usenewrc',_binary '0'),(4,_binary 'watchcreations',_binary '0'),(4,_binary 'watchdefault',_binary '0');
/*!40000 ALTER TABLE `zweig_user_properties` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_watchlist`
--

DROP TABLE IF EXISTS `zweig_watchlist`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_watchlist` (
  `wl_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `wl_user` int(10) unsigned NOT NULL,
  `wl_namespace` int(11) NOT NULL DEFAULT '0',
  `wl_title` varbinary(255) NOT NULL DEFAULT '',
  `wl_notificationtimestamp` varbinary(14) DEFAULT NULL,
  PRIMARY KEY (`wl_id`),
  UNIQUE KEY `wl_user` (`wl_user`,`wl_namespace`,`wl_title`),
  KEY `namespace_title` (`wl_namespace`,`wl_title`),
  KEY `wl_user_notificationtimestamp` (`wl_user`,`wl_notificationtimestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_watchlist`
--

LOCK TABLES `zweig_watchlist` WRITE;
/*!40000 ALTER TABLE `zweig_watchlist` DISABLE KEYS */;
INSERT INTO `zweig_watchlist` VALUES (1,2,0,_binary 'A_History_of_the_Stefan_Zweig_Bibliography',NULL),(2,2,0,_binary 'Baudelaire,_Charles_/_Individual_Poems',NULL),(3,2,0,_binary 'Magellan._Njeriu_dhe_vepra_e_tij_heroike:',NULL),(4,2,0,_binary 'Maria_Stouart',NULL),(5,2,0,_binary 'María_Stoúart',NULL),(6,2,0,_binary 'Nikol\'_skaia,_T.',NULL),(7,2,0,_binary 'Prochnik,_George',NULL),(8,2,0,_binary 'Pështjellim_ndjenjash',NULL),(9,2,0,_binary 'Sah',NULL),(10,2,0,_binary 'Sommernovellette',NULL),(11,2,0,_binary 'Sommernovellette_(VIST)',NULL),(12,2,0,_binary 'Stefan_Zweig._Die_geistige_Einheit_der_Welt',NULL),(13,2,0,_binary 'Stefan_Zweig_Bibliography',NULL),(14,2,0,_binary 'Warnung_an_Bibliophilen',NULL),(15,2,0,_binary 'Zweigheft',NULL),(16,2,0,_binary 'Zweigheft_/_zweigheft',NULL),(17,2,0,_binary 'Şah',NULL),(18,2,1,_binary 'A_History_of_the_Stefan_Zweig_Bibliography',NULL),(19,2,1,_binary 'Baudelaire,_Charles_/_Individual_Poems',NULL),(20,2,1,_binary 'Magellan._Njeriu_dhe_vepra_e_tij_heroike:',NULL),(21,2,1,_binary 'Maria_Stouart',NULL),(22,2,1,_binary 'María_Stoúart',NULL),(23,2,1,_binary 'Nikol\'_skaia,_T.',NULL),(24,2,1,_binary 'Prochnik,_George',NULL),(25,2,1,_binary 'Pështjellim_ndjenjash',NULL),(26,2,1,_binary 'Sah',NULL),(27,2,1,_binary 'Sommernovellette',NULL),(28,2,1,_binary 'Sommernovellette_(VIST)',NULL),(29,2,1,_binary 'Stefan_Zweig._Die_geistige_Einheit_der_Welt',NULL),(30,2,1,_binary 'Stefan_Zweig_Bibliography',NULL),(31,2,1,_binary 'Warnung_an_Bibliophilen',NULL),(32,2,1,_binary 'Zweigheft',NULL),(33,2,1,_binary 'Zweigheft_/_zweigheft',NULL),(34,2,1,_binary 'Şah',NULL),(35,2,12,_binary 'Editing',NULL),(36,2,13,_binary 'Editing',NULL),(37,2,14,_binary 'Collected_and_Selected_Works',NULL),(38,2,14,_binary 'Main',NULL),(39,2,14,_binary 'Secondary_Literatur_/_Authors_(Esperanto)',NULL),(40,2,14,_binary 'Secondary_Literature_/_Titles_(Portuguese)',NULL),(41,2,14,_binary 'Selected_Works_(German)',NULL),(42,2,15,_binary 'Collected_and_Selected_Works',NULL),(43,2,15,_binary 'Main',NULL),(44,2,15,_binary 'Secondary_Literatur_/_Authors_(Esperanto)',NULL),(45,2,15,_binary 'Secondary_Literature_/_Titles_(Portuguese)',NULL),(46,2,15,_binary 'Selected_Works_(German)',NULL),(47,3,0,_binary 'Stefan_Zweig_Bibliography',NULL),(48,3,1,_binary 'Stefan_Zweig_Bibliography',NULL);
/*!40000 ALTER TABLE `zweig_watchlist` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `zweig_watchlist_expiry`
--

DROP TABLE IF EXISTS `zweig_watchlist_expiry`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `zweig_watchlist_expiry` (
  `we_item` int(10) unsigned NOT NULL,
  `we_expiry` binary(14) NOT NULL,
  PRIMARY KEY (`we_item`),
  KEY `we_expiry` (`we_expiry`)
) ENGINE=InnoDB DEFAULT CHARSET=binary;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `zweig_watchlist_expiry`
--

LOCK TABLES `zweig_watchlist_expiry` WRITE;
/*!40000 ALTER TABLE `zweig_watchlist_expiry` DISABLE KEYS */;
/*!40000 ALTER TABLE `zweig_watchlist_expiry` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2021-08-27 15:00:48
