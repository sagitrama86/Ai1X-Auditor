-- ============================================
-- AI1X Auditor — MySQL Schema
-- Generated from YAML definitions
-- ============================================

CREATE DATABASE IF NOT EXISTS HEDIS_RDW;
USE HEDIS_RDW;

-- --------------------------------------------
-- dimorganization
-- Organization/client dimension. One row per health plan that reports HEDIS.
-- --------------------------------------------
DROP TABLE IF EXISTS `dimorganization`;
CREATE TABLE `dimorganization` (
  `organizationid` INT NOT NULL,
  `organizationname` VARCHAR(200) NOT NULL,
  PRIMARY KEY (`organizationid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- dimproductcategory
-- Maps ProductCategoryID to LOB names (Commercial, Medicaid, Medicare).
-- --------------------------------------------
DROP TABLE IF EXISTS `dimproductcategory`;
CREATE TABLE `dimproductcategory` (
  `ProductCategoryID` INT NOT NULL,
  `productcategoryname` VARCHAR(100) NOT NULL,
  PRIMARY KEY (`ProductCategoryID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- dimprovidergroup
-- Provider group dimension. One row per provider group per domain.
-- --------------------------------------------
DROP TABLE IF EXISTS `dimprovidergroup`;
CREATE TABLE `dimprovidergroup` (
  `providerGroupID` INT NOT NULL,
  `domainid` INT NOT NULL,
  `providerGroupName` VARCHAR(200) NOT NULL,
  PRIMARY KEY (`providerGroupID`, `domainid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- dimprovider_RDM
-- Provider Reference Data Management dimension. Individual provider details.
-- --------------------------------------------
DROP TABLE IF EXISTS `dimprovider_RDM`;
CREATE TABLE `dimprovider_RDM` (
  `domainid` INT NOT NULL,
  `sourcesystemuniqueidentifier` VARCHAR(50) NOT NULL,
  `providerNPI` VARCHAR(20) NULL,
  `specialty` VARCHAR(100) NULL,
  PRIMARY KEY (`domainid`, `sourcesystemuniqueidentifier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- qualitycutpoints
-- NCQA percentile cutpoints for quality measures. Defines thresholds for <25th, 25th, 50th, 75th, 90th
-- --------------------------------------------
DROP TABLE IF EXISTS `qualitycutpoints`;
CREATE TABLE `qualitycutpoints` (
  `organizationId` INT NOT NULL,
  `ProductCategoryId` INT NOT NULL,
  `domainid` INT NOT NULL,
  `MeasurementYear` VARCHAR(4) NOT NULL,
  `SubMeasureCode` VARCHAR(20) NOT NULL,
  `Cutpoint3` DECIMAL(5,2) NULL,
  `Cutpoint5` DECIMAL(5,2) NULL,
  `Cutpoint7` DECIMAL(5,2) NULL,
  `Cutpoint8` DECIMAL(5,2) NULL,
  PRIMARY KEY (`organizationId`, `ProductCategoryId`, `domainid`, `MeasurementYear`, `SubMeasureCode`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- keyvaluemapping
-- Lookup table for measure merging and key-value translations. Maps old measure codes to new ones via 
-- --------------------------------------------
DROP TABLE IF EXISTS `keyvaluemapping`;
CREATE TABLE `keyvaluemapping` (
  `KeyName` VARCHAR(50) NOT NULL,
  `KEYVALUE` VARCHAR(50) NULL,
  `ADDITIONALKEY1` VARCHAR(50) NOT NULL DEFAULT '',
  `ADDITIONALKEY2` VARCHAR(50) NOT NULL DEFAULT '',
  `SubModuleName` VARCHAR(50) NOT NULL DEFAULT '',
  PRIMARY KEY (`KeyName`, `ADDITIONALKEY1`, `ADDITIONALKEY2`, `SubModuleName`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- measuredetails
-- Dimension table containing HEDIS measure definitions. One row per measure. Contains measure codes, n
-- --------------------------------------------
DROP TABLE IF EXISTS `measuredetails`;
CREATE TABLE `measuredetails` (
  `measureid` INT NOT NULL,
  `clinicalmeasureid` INT NOT NULL,
  `submeasurecode` VARCHAR(20) NOT NULL,
  `name` VARCHAR(200) NOT NULL,
  `measurecode` VARCHAR(10) NOT NULL,
  `measuretype` VARCHAR(30) NOT NULL,
  `STARINDICATOR` CHAR(1) NULL,
  `InverseFlag` CHAR(1) NULL,
  `NCQAInvertedFlag` CHAR(1) NULL,
  `CMQDOMAIN` VARCHAR(100) NULL,
  `category` VARCHAR(100) NULL,
  PRIMARY KEY (`measureid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- factqualityreport
-- Primary fact table for HEDIS quality reporting. Contains one row per member per measure per submissi
-- --------------------------------------------
DROP TABLE IF EXISTS `factqualityreport`;
CREATE TABLE `factqualityreport` (
  `factssui` BIGINT NOT NULL,
  `SubmissionId` INT NOT NULL,
  `organizationid` INT NOT NULL,
  `organizationname` VARCHAR(200) NOT NULL,
  `clinicalmeasureid` INT NULL,
  `keyvaluemeasureid` INT NULL,
  `submeasurecode` VARCHAR(20) NOT NULL,
  `Act_Performance_Met` INT NOT NULL,
  `Act_Performance_Not_Met` INT NOT NULL,
  `reportingExclusionStatus` INT NOT NULL,
  `clinicalonlystatus` INT NOT NULL,
  `patientSSUI` VARCHAR(50) NULL,
  `visitSSUI` VARCHAR(50) NULL,
  `eventSSUI` VARCHAR(50) NULL,
  `isRau` TINYINT(1) NOT NULL,
  `isUtilization` TINYINT(1) NOT NULL,
  `enrollmentStatus` VARCHAR(20) NOT NULL,
  `NCQA_Submission_ID_Name` VARCHAR(100) NOT NULL,
  `MeasurementYear` VARCHAR(10) NOT NULL,
  `initiativeyear` VARCHAR(4) NOT NULL,
  `providerGroupID` INT NOT NULL,
  `KeyToProvider` VARCHAR(50) NOT NULL,
  `ProductCategoryID` INT NOT NULL,
  `domainid` INT NOT NULL,
  `minimumrequiredsamplesize` INT NULL,
  `submissionsourcesfeedtype` VARCHAR(50) NULL,
  `oversample` VARCHAR(10) NULL,
  PRIMARY KEY (`factssui`, `SubmissionId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- factQualityReport_Filters
-- Companion filter table to factqualityreport. Contains attribution model details, provider assignment
-- --------------------------------------------
DROP TABLE IF EXISTS `factQualityReport_Filters`;
CREATE TABLE `factQualityReport_Filters` (
  `factssui` BIGINT NOT NULL,
  `SubmissionId` INT NOT NULL,
  `productname` VARCHAR(200) NULL,
  `healthplanname` VARCHAR(200) NULL,
  `attributionmodelcode` VARCHAR(20) NULL,
  `assignedprovidergroupname` VARCHAR(200) NULL,
  `assignedprovidername` VARCHAR(200) NULL,
  `assignedproviderfname` VARCHAR(100) NULL,
  `assignedproviderlname` VARCHAR(100) NULL,
  `Subnetwork` VARCHAR(100) NULL,
  `businessgroupcode` VARCHAR(20) NULL,
  `assignedprovidergroupid` INT NULL,
  `assignedproviderid` INT NULL,
  PRIMARY KEY (`factssui`, `SubmissionId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------
-- Indexes
-- --------------------------------------------
CREATE INDEX idx_fqr_org ON factqualityreport (organizationid);
CREATE INDEX idx_fqr_measure ON factqualityreport (submeasurecode);
CREATE INDEX idx_fqr_year ON factqualityreport (MeasurementYear);
CREATE INDEX idx_fqr_clinical ON factqualityreport (clinicalonlystatus);
CREATE INDEX idx_fqr_kvmid ON factqualityreport (keyvaluemeasureid);
CREATE INDEX idx_fqr_cmid ON factqualityreport (clinicalmeasureid);
CREATE INDEX idx_fqr_ktp ON factqualityreport (KeyToProvider);
CREATE INDEX idx_md_cmid ON measuredetails (clinicalmeasureid);
CREATE INDEX idx_md_smc ON measuredetails (submeasurecode);

-- --------------------------------------------
-- Foreign Keys
-- --------------------------------------------
ALTER TABLE factqualityreport ADD CONSTRAINT fk_fqr_org FOREIGN KEY (organizationid) REFERENCES dimorganization(organizationid);
ALTER TABLE factqualityreport ADD CONSTRAINT fk_fqr_product FOREIGN KEY (ProductCategoryID) REFERENCES dimproductcategory(ProductCategoryID);
ALTER TABLE factQualityReport_Filters ADD CONSTRAINT fk_fqrf_fqr FOREIGN KEY (factssui, SubmissionId) REFERENCES factqualityreport(factssui, SubmissionId);

-- NOTE: These joins cannot be expressed as standard FKs:
-- factqualityreport → measuredetails (conditional OR join)
-- factqualityreport → dimprovider_RDM (CONCAT-based join)
-- factqualityreport → qualitycutpoints (5-column composite, LEFT JOIN)
-- factqualityreport → keyvaluemapping (complex expression, LEFT JOIN)
