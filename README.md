# Repo for the CS 224W project using the DIME datasest

# Layout of the Data/ directory

## Data/CSVs

* Stores the raw, unzipped CSV files downloaded from DIME
* Filenames for transactions follow pattern Data/CSVs/contribDB\_*year*.csv
* Candidates in file Data/CSVs/candidate\_cfscores\_st\_fed\_1979\_2012.csv
* Contributors in file Data/CSVs/contributor\_cfscores\_st\_fed\_1979\_2012.csv

## Data/DBs

* Stores the SQL DB files created from the CSVs, one per cycle
* Filenames follow pattern Data/DBs/*year*.db

## Data/Bipartite-Graphs

* Stores the bipartite (donor-candidate) graphs created in snap.py, one per cycle
* Filenames follow pattern Data/Bipartite-Graphs/<year>.graph

## Data/Mappings

* Stores the mappings from primary keys for the SQL tables to the node/edge IDs
* Filenames follow pattern Data/Mappings/*year*.(edge/recips/contribs)

# Schemas for the databases:

## Recipients

* year INTEGER,                // The election cycle this particular campaign was for
* rid TEXT,                    // A unique ID assigned to each recipient that lasts across cycles and campaigns
* cid INTEGER,                 // A unique ID assigned to each contributor that lasts across cycles and campaigns
* party INTEGER,               // 1 if Dem, 2 if GOP, 3 if other (indepedent, 3rd party, whatever)
* seat TEXT,                   // The office being sought (e.g. presidency, US Senate, State House)
* district VARCHAR(8),         // A code for the candidate's district
* incumb INTEGER,              // 0 if open seat, 1 if incumbent, 2 if challenger
* cfs REAL,                    // Overall candidate CFscore
* cfsdyn REAL,                 // CFscore for that particular election cycle, assuming contributor ideologies never change
* numgivers INTEGER,           // Total number of donations received
* gender INTEGER,              // 1 if female (F), 0 if male (M)
* didprimary INTEGER,          // 1 if participated in primary 0 otherwise
* winner INTEGER,              // 1 if won, 0 if lost
* partisanship REAL,   // Kernell's (2009) measurement of district partisanship for current cycle
* indistrict REAL,             // Proportion of donations coming from donors within the district
* instate REAL,                // Proportion of donations coming from donors within the state
* candstatus INTEGER,          // 1 if statutory candidate (C), 2 if statutory candidate for future cycle (F), 3 if not yet statutory candidate (N), 4 if statutory candidate in prior cycle (P)
* fecyear INTEGER,             // The election cycle a candidate is fundraising for. May differ from year for e.g. a Senator doing re-election fundraising during their first four years
* candorcomm INTEGER,          // 1 if candidate, 0 if committee
* PRIMARY KEY(year, rid, seat) // The combination of a person/committee (rid), an office (seat), and a year make a unique campaign

## Contributors:

* cid INTEGER PRIMARY KEY,     // A unique id for each donor
* indiv INTEGER,               // 1 if donor is individual, 0 if donor is committee/organization
* state VARCHAR(4),            // State in which donor resides
* cfscore REAL                 // CFscore of donor

## Transactions:

* year INTEGER,                // The cycle during which the trasnaction occurred
* tid TEXT,                    // A text ID for the transaction (unique per cycle)
* ttid VARCHAR(4),             // The transaction type
* amount INTEGER,              // The transaction amount
* date VARCHAR(10),            // The transaction date
* cid INTEGER,                 // The contributor ID
* indiv INTEGER,               // 1 if donor is individual, 0 if donor is committee/organization
* rid TEXT,                    // The recipient ID
* party INTEGER,               // 1 if Dem, 2 if GOP, 3 if other (indepedent, 3rd party, whatever)
* candorcomm INTEGER,          // 1 if candidate, 0 if committee
* district VARCHAR(8),         // A code for the candidate's district
* seat TEXT,                   // The office being sought
* cfscore REAL                 // CFscore of donor
* cfs REAL,                    // Overall candidate CFscore
* PRIMARY KEY(year, tid),
* FOREIGN KEY(cid) REFERENCES Contributors(cid),
* FOREIGN KEY(rid) REFERENCES Recipients(rid),
* FOREIGN KEY(seat) REFERENCES Recipients(seat)

## Attributes on Bipartite Graph Nodes:

* IsRecip is 0: contributor, 1: recipient with CFScore, or 2: recipipent without CFScore
