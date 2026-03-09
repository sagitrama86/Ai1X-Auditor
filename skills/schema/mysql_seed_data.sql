-- ============================================
-- AI1X Auditor — MySQL Sample Data
-- Realistic HEDIS quality reporting test data
-- ============================================

USE HEDIS_RDW;

-- --------------------------------------------
-- dimorganization (5 health plans)
-- --------------------------------------------
INSERT INTO dimorganization (organizationid, organizationname) VALUES
(1001, 'Acme Health Plan'),
(1002, 'BlueStar Insurance'),
(1003, 'Meridian Health Partners'),
(1004, 'Pacific Care Alliance'),
(1005, 'Summit Health Group');

-- --------------------------------------------
-- dimproductcategory (3 LOBs)
-- --------------------------------------------
INSERT INTO dimproductcategory (ProductCategoryID, productcategoryname) VALUES
(1, 'Commercial'),
(2, 'Medicaid'),
(3, 'Medicare');

-- --------------------------------------------
-- dimprovidergroup (10 groups across 2 domains)
-- --------------------------------------------
INSERT INTO dimprovidergroup (providerGroupID, domainid, providerGroupName) VALUES
(100, 1, 'Metro Primary Care Network'),
(101, 1, 'Valley Pediatrics Group'),
(102, 1, 'Coastal Family Medicine'),
(103, 1, 'Summit Specialty Partners'),
(104, 1, 'Riverside Health Associates'),
(200, 2, 'Downtown Medical Group'),
(201, 2, 'Lakeside Wellness Center'),
(202, 2, 'Mountain View Clinic'),
(203, 2, 'Harbor Health Services'),
(204, 2, 'Sunrise Medical Associates');

-- --------------------------------------------
-- dimprovider_RDM (20 providers)
-- --------------------------------------------
INSERT INTO dimprovider_RDM (domainid, sourcesystemuniqueidentifier, providerNPI, specialty) VALUES
(1, 'PAT00101', '1234567890', 'Family Medicine'),
(1, 'PAT00102', '1234567891', 'Pediatrics'),
(1, 'PAT00103', '1234567892', 'Internal Medicine'),
(1, 'PAT00104', '1234567893', 'OB/GYN'),
(1, 'PAT00105', '1234567894', 'Cardiology'),
(1, 'PAT00106', '1234567895', 'Endocrinology'),
(1, 'PAT00107', '1234567896', 'Ophthalmology'),
(1, 'PAT00108', '1234567897', 'Psychiatry'),
(1, 'PAT00109', '1234567898', 'Pulmonology'),
(1, 'PAT00110', '1234567899', 'Oncology'),
(2, 'EVT00201', '2345678901', 'Family Medicine'),
(2, 'EVT00202', '2345678902', 'Pediatrics'),
(2, 'EVT00203', '2345678903', 'Internal Medicine'),
(2, 'EVT00204', '2345678904', 'OB/GYN'),
(2, 'EVT00205', '2345678905', 'Cardiology'),
(2, 'EVT00206', '2345678906', 'Endocrinology'),
(2, 'EVT00207', '2345678907', 'Dermatology'),
(2, 'EVT00208', '2345678908', 'Psychiatry'),
(2, 'EVT00209', '2345678909', 'Neurology'),
(2, 'EVT00210', '2345678910', 'Gastroenterology');

-- --------------------------------------------
-- measuredetails (8 measures, 18 sub-measures)
-- --------------------------------------------
INSERT INTO measuredetails (measureid, clinicalmeasureid, submeasurecode, name, measurecode, measuretype, STARINDICATOR, InverseFlag, NCQAInvertedFlag, CMQDOMAIN, category) VALUES
(1,  1001, 'AWC-01', 'Adolescent Well-Care Visits',                          'AWC', 'Visit',           'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(2,  1002, 'BCS-01', 'Breast Cancer Screening',                              'BCS', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(3,  1003, 'CBP-01', 'Controlling High Blood Pressure',                      'CBP', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Chronic'),
(4,  1004, 'CIS-01', 'Childhood Immunization Status — DTaP',                 'CIS', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(5,  1005, 'CIS-02', 'Childhood Immunization Status — IPV',                  'CIS', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(6,  1006, 'CIS-03', 'Childhood Immunization Status — MMR',                  'CIS', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(7,  1007, 'CIS-10', 'Childhood Immunization Status — Combo 10',             'CIS', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(8,  1008, 'COL-01', 'Colorectal Cancer Screening',                          'COL', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(9,  1009, 'CDC-01', 'Comprehensive Diabetes Care — HbA1c Testing',          'CDC', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Chronic'),
(10, 1010, 'CDC-02', 'Comprehensive Diabetes Care — HbA1c Poor Control',     'CDC', 'Patient-Process',  'Y', 'Y', 'Y', 'Effectiveness of Care', 'Chronic'),
(11, 1011, 'CDC-03', 'Comprehensive Diabetes Care — HbA1c Good Control',     'CDC', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Chronic'),
(12, 1012, 'FUA-01', 'Follow-Up After ED Visit for AOD — 7 Day',            'FUA', 'Event',            NULL, 'N', 'N', 'Effectiveness of Care', 'Behavioral Health'),
(13, 1013, 'FUA-02', 'Follow-Up After ED Visit for AOD — 30 Day',           'FUA', 'Event',            NULL, 'N', 'N', 'Effectiveness of Care', 'Behavioral Health'),
(14, 1014, 'PCE-01', 'Pharmacotherapy Management of COPD Exacerbation',      'PCE', 'Event',            NULL, 'Y', 'Y', 'Effectiveness of Care', 'Chronic'),
(15, 1015, 'WCC-01', 'Weight Assessment — BMI Percentile',                   'WCC', 'Patient-Process',  NULL, 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(16, 1016, 'WCC-02', 'Weight Assessment — Counseling for Nutrition',         'WCC', 'Patient-Process',  NULL, 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(17, 1017, 'WCC-03', 'Weight Assessment — Counseling for Physical Activity', 'WCC', 'Patient-Process',  NULL, 'N', 'N', 'Effectiveness of Care', 'Prevention'),
(18, 1018, 'IMA-01', 'Immunizations for Adolescents — Combo 2',             'IMA', 'Patient-Process',  'Y', 'N', 'N', 'Effectiveness of Care', 'Prevention');

-- --------------------------------------------
-- qualitycutpoints (cutpoints for org 1001, Commercial, 2024)
-- --------------------------------------------
INSERT INTO qualitycutpoints (organizationId, ProductCategoryId, domainid, MeasurementYear, SubMeasureCode, Cutpoint3, Cutpoint5, Cutpoint7, Cutpoint8) VALUES
(1001, 1, 1, '2024', 'AWC-01', 45.00, 55.00, 65.00, 75.00),
(1001, 1, 1, '2024', 'BCS-01', 60.00, 70.00, 78.00, 85.00),
(1001, 1, 1, '2024', 'CBP-01', 55.00, 63.00, 72.00, 80.00),
(1001, 1, 1, '2024', 'CIS-01', 70.00, 78.00, 85.00, 90.00),
(1001, 1, 1, '2024', 'CIS-02', 72.00, 80.00, 87.00, 92.00),
(1001, 1, 1, '2024', 'CIS-03', 75.00, 82.00, 88.00, 93.00),
(1001, 1, 1, '2024', 'CIS-10', 30.00, 40.00, 50.00, 60.00),
(1001, 1, 1, '2024', 'COL-01', 50.00, 60.00, 70.00, 78.00),
(1001, 1, 1, '2024', 'CDC-01', 80.00, 85.00, 90.00, 95.00),
(1001, 1, 1, '2024', 'CDC-02', 50.00, 42.00, 35.00, 28.00),
(1001, 1, 1, '2024', 'CDC-03', 40.00, 50.00, 58.00, 65.00),
(1001, 1, 1, '2024', 'FUA-01', 10.00, 15.00, 22.00, 30.00),
(1001, 1, 1, '2024', 'FUA-02', 15.00, 22.00, 30.00, 40.00),
(1001, 1, 1, '2024', 'PCE-01', 60.00, 52.00, 45.00, 38.00),
(1001, 2, 1, '2024', 'AWC-01', 40.00, 50.00, 60.00, 70.00),
(1001, 2, 1, '2024', 'BCS-01', 55.00, 65.00, 73.00, 80.00),
(1001, 2, 1, '2024', 'CBP-01', 50.00, 58.00, 67.00, 75.00),
(1001, 3, 1, '2024', 'AWC-01', 42.00, 52.00, 62.00, 72.00),
(1001, 3, 1, '2024', 'BCS-01', 58.00, 68.00, 76.00, 83.00),
(1002, 1, 1, '2024', 'AWC-01', 45.00, 55.00, 65.00, 75.00),
(1002, 1, 1, '2024', 'BCS-01', 60.00, 70.00, 78.00, 85.00),
(1002, 1, 1, '2024', 'CBP-01', 55.00, 63.00, 72.00, 80.00),
(1002, 1, 1, '2024', 'CDC-01', 80.00, 85.00, 90.00, 95.00),
(1002, 1, 1, '2024', 'CDC-02', 50.00, 42.00, 35.00, 28.00),
(1002, 1, 1, '2024', 'COL-01', 50.00, 60.00, 70.00, 78.00);

-- --------------------------------------------
-- keyvaluemapping (measure merges)
-- --------------------------------------------
INSERT INTO keyvaluemapping (KeyName, KEYVALUE, ADDITIONALKEY1, ADDITIONALKEY2, SubModuleName) VALUES
('CIS-01', 'CIS-01', '4', '2024', 'Measure_Merge'),
('CIS-02', 'CIS-02', '5', '2024', 'Measure_Merge'),
('CIS-03', 'CIS-03', '6', '2024', 'Measure_Merge'),
('CIS-10', 'CIS-10', '7', '2024', 'Measure_Merge'),
('WCC-01', 'WCC-01', '15', '2024', 'Measure_Merge'),
('WCC-02', 'WCC-02', '16', '2024', 'Measure_Merge');

-- --------------------------------------------
-- factqualityreport — generate ~500 rows
-- Covers 5 orgs × 3 LOBs × 18 measures × 2 submissions
-- with realistic clinical status distribution
-- --------------------------------------------

-- Helper: Use a stored procedure to generate data
DELIMITER //
CREATE PROCEDURE generate_fact_data()
BEGIN
    DECLARE v_factssui BIGINT DEFAULT 1000000;
    DECLARE v_orgid INT;
    DECLARE v_orgname VARCHAR(200);
    DECLARE v_prodid INT;
    DECLARE v_measid INT;
    DECLARE v_cmeasid INT;
    DECLARE v_smc VARCHAR(20);
    DECLARE v_mtype VARCHAR(30);
    DECLARE v_subid INT;
    DECLARE v_subname VARCHAR(100);
    DECLARE v_status INT;
    DECLARE v_met INT;
    DECLARE v_notmet INT;
    DECLARE v_excl INT;
    DECLARE v_domid INT DEFAULT 1;
    DECLARE v_year VARCHAR(10) DEFAULT '2024';
    DECLARE v_pgid INT;
    DECLARE v_ktp VARCHAR(50);
    DECLARE v_patient_count INT;
    DECLARE v_i INT;

    -- For each org
    DECLARE org_cursor CURSOR FOR SELECT organizationid, organizationname FROM dimorganization;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET @done = TRUE;

    OPEN org_cursor;
    org_loop: LOOP
        FETCH org_cursor INTO v_orgid, v_orgname;
        IF @done THEN LEAVE org_loop; END IF;

        -- For each product (LOB)
        SET v_prodid = 1;
        prod_loop: WHILE v_prodid <= 3 DO

            -- For each measure
            SET v_measid = 1;
            meas_loop: WHILE v_measid <= 18 DO

                SELECT clinicalmeasureid, submeasurecode, measuretype
                INTO v_cmeasid, v_smc, v_mtype
                FROM measuredetails WHERE measureid = v_measid;

                -- For each submission (1 and 2)
                SET v_subid = 1;
                sub_loop: WHILE v_subid <= 2 DO
                    SET v_subname = CONCAT('Submission ', v_subid);

                    -- Generate 3-8 members per measure/org/product/submission
                    SET v_patient_count = 3 + FLOOR(RAND() * 6);
                    SET v_i = 0;

                    patient_loop: WHILE v_i < v_patient_count DO
                        SET v_factssui = v_factssui + 1;

                        -- Assign provider group and provider
                        SET v_pgid = 100 + FLOOR(RAND() * 5);
                        SET v_ktp = CONCAT(v_domid, '-PAT', LPAD(v_factssui MOD 10000, 5, '0'));

                        -- Clinical status distribution: 80% DE(17), 8% DVDE(16), 6% ECC(23), 6% ERF(24)
                        SET v_status = ELT(1 + FLOOR(RAND() * 50),
                            17,17,17,17,17,17,17,17,17,17,
                            17,17,17,17,17,17,17,17,17,17,
                            17,17,17,17,17,17,17,17,17,17,
                            17,17,17,17,17,17,17,17,17,17,
                            16,16,16,16,
                            23,23,23,
                            24,24,24);

                        -- Performance: ~70% compliant for DE rows
                        IF v_status = 17 THEN
                            SET v_met = IF(RAND() < 0.70, 1, 0);
                            SET v_notmet = 1 - v_met;
                            SET v_excl = 0;
                        ELSE
                            SET v_met = 0;
                            SET v_notmet = 0;
                            SET v_excl = IF(v_status IN (23, 24), 1, 0);
                        END IF;

                        INSERT INTO factqualityreport (
                            factssui, SubmissionId, organizationid, organizationname,
                            clinicalmeasureid, keyvaluemeasureid, submeasurecode,
                            Act_Performance_Met, Act_Performance_Not_Met, reportingExclusionStatus,
                            clinicalonlystatus, patientSSUI, visitSSUI, eventSSUI,
                            isRau, isUtilization, enrollmentStatus,
                            NCQA_Submission_ID_Name, MeasurementYear, initiativeyear,
                            providerGroupID, KeyToProvider, ProductCategoryID, domainid,
                            minimumrequiredsamplesize, submissionsourcesfeedtype, oversample
                        ) VALUES (
                            v_factssui, v_subid, v_orgid, v_orgname,
                            v_cmeasid, v_measid, v_smc,
                            v_met, v_notmet, v_excl,
                            v_status,
                            IF(v_mtype = 'Patient-Process', CONCAT('P', v_factssui), NULL),
                            IF(v_mtype = 'Visit', CONCAT('V', v_factssui), NULL),
                            IF(v_mtype = 'Event', CONCAT('E', v_factssui), NULL),
                            0, 0, 'Enrolled',
                            v_subname, v_year, '2024',
                            v_pgid, v_ktp, v_prodid, v_domid,
                            IF(RAND() < 0.3, 411, NULL),
                            ELT(1 + FLOOR(RAND() * 3), 'Administrative', 'Supplemental', 'Hybrid'),
                            NULL
                        );

                        -- Also insert into Filters table
                        INSERT INTO factQualityReport_Filters (
                            factssui, SubmissionId, productname, healthplanname,
                            attributionmodelcode, assignedprovidergroupname, assignedprovidername,
                            assignedproviderfname, assignedproviderlname, Subnetwork,
                            businessgroupcode, assignedprovidergroupid, assignedproviderid
                        ) VALUES (
                            v_factssui, v_subid,
                            ELT(v_prodid, 'Commercial PPO', 'Medicaid HMO', 'Medicare Advantage'),
                            CONCAT(v_orgname, ' - ', ELT(v_prodid, 'PPO Plan', 'HMO Plan', 'MA Plan')),
                            ELT(1 + FLOOR(RAND() * 3), 'PCP', 'SPECIALIST', 'FACILITY'),
                            ELT(1 + FLOOR(RAND() * 5), 'Metro Primary Care Network', 'Valley Pediatrics Group', 'Coastal Family Medicine', 'Summit Specialty Partners', 'Riverside Health Associates'),
                            ELT(1 + FLOOR(RAND() * 6), 'Smith, John', 'Johnson, Sarah', 'Williams, Michael', 'Brown, Emily', 'Davis, Robert', '-1'),
                            ELT(1 + FLOOR(RAND() * 5), 'John', 'Sarah', 'Michael', 'Emily', 'Robert'),
                            ELT(1 + FLOOR(RAND() * 5), 'Smith', 'Johnson', 'Williams', 'Brown', 'Davis'),
                            ELT(1 + FLOOR(RAND() * 4), 'North Region', 'South Region', 'East Region', 'West Region'),
                            ELT(1 + FLOOR(RAND() * 3), 'BG-COMM', 'BG-GOVT', 'BG-SENIOR'),
                            v_pgid,
                            1000 + FLOOR(RAND() * 500)
                        );

                        SET v_i = v_i + 1;
                    END WHILE patient_loop;

                    SET v_subid = v_subid + 1;
                END WHILE sub_loop;

                SET v_measid = v_measid + 1;
            END WHILE meas_loop;

            SET v_prodid = v_prodid + 1;
        END WHILE prod_loop;

    END LOOP org_loop;
    CLOSE org_cursor;

    -- Add some isRau=1 rows (should be excluded from quality reports)
    SET v_factssui = v_factssui + 1;
    INSERT INTO factqualityreport VALUES (v_factssui, 1, 1001, 'Acme Health Plan', 1001, 1, 'AWC-01', 1, 0, 0, 17, NULL, CONCAT('V',v_factssui), NULL, 1, 0, 'Enrolled', 'Submission 1', '2024', '2024', 100, CONCAT('1-PAT',v_factssui MOD 10000), 1, 1, NULL, 'Administrative', NULL);
    INSERT INTO factQualityReport_Filters VALUES (v_factssui, 1, 'Commercial PPO', 'Acme Health Plan - PPO Plan', 'PCP', 'Metro Primary Care Network', 'Smith, John', 'John', 'Smith', 'North Region', 'BG-COMM', 100, 1001);

    SET v_factssui = v_factssui + 1;
    INSERT INTO factqualityreport VALUES (v_factssui, 1, 1001, 'Acme Health Plan', 1001, 1, 'AWC-01', 0, 1, 0, 17, NULL, CONCAT('V',v_factssui), NULL, 1, 0, 'Enrolled', 'Submission 1', '2024', '2024', 100, CONCAT('1-PAT',v_factssui MOD 10000), 1, 1, NULL, 'Administrative', NULL);
    INSERT INTO factQualityReport_Filters VALUES (v_factssui, 1, 'Commercial PPO', 'Acme Health Plan - PPO Plan', 'PCP', 'Metro Primary Care Network', 'Johnson, Sarah', 'Sarah', 'Johnson', 'South Region', 'BG-COMM', 100, 1002);

    -- Add some isUtilization=1 rows (should also be excluded)
    SET v_factssui = v_factssui + 1;
    INSERT INTO factqualityreport VALUES (v_factssui, 1, 1002, 'BlueStar Insurance', 1002, 2, 'BCS-01', 1, 0, 0, 17, CONCAT('P',v_factssui), NULL, NULL, 0, 1, 'Enrolled', 'Submission 1', '2024', '2024', 101, CONCAT('1-PAT',v_factssui MOD 10000), 1, 1, NULL, 'Administrative', NULL);
    INSERT INTO factQualityReport_Filters VALUES (v_factssui, 1, 'Commercial PPO', 'BlueStar Insurance - PPO Plan', 'PCP', 'Valley Pediatrics Group', 'Williams, Michael', 'Michael', 'Williams', 'East Region', 'BG-COMM', 101, 1003);

    -- Add duplicate rows (to test deduplication with ROW_NUMBER)
    SET v_factssui = v_factssui + 1;
    INSERT INTO factqualityreport VALUES (v_factssui, 1, 1001, 'Acme Health Plan', 1003, 3, 'CBP-01', 1, 0, 0, 17, CONCAT('P',v_factssui), NULL, NULL, 0, 0, 'Enrolled', 'Submission 1', '2024', '2024', 102, CONCAT('1-PAT',v_factssui MOD 10000), 1, 1, NULL, 'Administrative', NULL);
    INSERT INTO factQualityReport_Filters VALUES (v_factssui, 1, 'Commercial PPO', 'Acme Health Plan - PPO Plan', 'PCP', 'Coastal Family Medicine', 'Brown, Emily', 'Emily', 'Brown', 'West Region', 'BG-COMM', 102, 1004);
    -- Duplicate with same factssui different submission
    INSERT INTO factqualityreport VALUES (v_factssui, 2, 1001, 'Acme Health Plan', 1003, 3, 'CBP-01', 1, 0, 0, 17, CONCAT('P',v_factssui), NULL, NULL, 0, 0, 'Enrolled', 'Submission 2', '2024', '2024', 102, CONCAT('1-PAT',v_factssui MOD 10000), 1, 1, NULL, 'Administrative', NULL);
    INSERT INTO factQualityReport_Filters VALUES (v_factssui, 2, 'Commercial PPO', 'Acme Health Plan - PPO Plan', 'PCP', 'Coastal Family Medicine', 'Brown, Emily', 'Emily', 'Brown', 'West Region', 'BG-COMM', 102, 1004);

    SELECT CONCAT('Generated ', v_factssui - 1000000, ' fact rows') AS result;
END //
DELIMITER ;

CALL generate_fact_data();
DROP PROCEDURE generate_fact_data;

-- --------------------------------------------
-- Verify counts
-- --------------------------------------------
SELECT 'dimorganization' AS tbl, COUNT(*) AS cnt FROM dimorganization
UNION ALL SELECT 'dimproductcategory', COUNT(*) FROM dimproductcategory
UNION ALL SELECT 'dimprovidergroup', COUNT(*) FROM dimprovidergroup
UNION ALL SELECT 'dimprovider_RDM', COUNT(*) FROM dimprovider_RDM
UNION ALL SELECT 'measuredetails', COUNT(*) FROM measuredetails
UNION ALL SELECT 'qualitycutpoints', COUNT(*) FROM qualitycutpoints
UNION ALL SELECT 'keyvaluemapping', COUNT(*) FROM keyvaluemapping
UNION ALL SELECT 'factqualityreport', COUNT(*) FROM factqualityreport
UNION ALL SELECT 'factQualityReport_Filters', COUNT(*) FROM factQualityReport_Filters;
