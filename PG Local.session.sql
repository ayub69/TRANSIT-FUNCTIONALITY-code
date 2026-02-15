CREATE TABLE bus_routes
(
    route_id SERIAL PRIMARY KEY,
    route_number VARCHAR(50) NOT NULL,
    route_type VARCHAR(50) NOT NULL,
    start_point VARCHAR(255) NOT NULL,
    end_point VARCHAR(255) NOT NULL,
    route_length_km FLOAT,
    fare INT
);

CREATE TABLE bus_stops
(
    stop_id SERIAL PRIMARY KEY,
    stop_name VARCHAR(255) UNIQUE NOT NULL,
    latitude FLOAT,
    longitude FLOAT
);

CREATE TABLE transfer_stops
(
    id SERIAL PRIMARY KEY,
    route_id INT REFERENCES bus_routes(route_id) ON DELETE CASCADE,
    stop_id INT REFERENCES bus_stops(stop_id) ON DELETE CASCADE,
    stop_order INT NOT NULL
);


-----------inserting values in bus_routes------------

--for red bus
INSERT INTO bus_routes (route_number, route_type, start_point, end_point, route_length_km, fare)
VALUES ('Route 1', 'Red', 'Khokrapar', 'Dockyard', 28, 120);
INSERT INTO bus_routes (route_number, route_type, start_point, end_point, route_length_km, fare)
VALUES ('Route 2', 'Red', 'Power House', 'Indus Hospital', 30, 120),
('Route 3', 'Red', 'Power House', 'Nasir Jump', 31, 120);
INSERT INTO bus_routes (route_number, route_type, start_point, end_point, route_length_km, fare)
VALUES ('Route 4', 'Red', 'Power House', 'keamari', 21, 120),
('Route 8', 'Red', 'Yousuf Goth', 'Tower', 17, 120),
('Route 9', 'Red', 'Gulshan e Hadeed', 'Tower', 42, 120),
('Route 10', 'Red', 'Numaish Chowrangi', 'Ibrahim Hyderi', 28, 120),
('Route 11', 'Red', 'Miran Nakka', 'Shireen Jinnah Colony', 19, 120),
('Route 12', 'Red', 'Naddi Kinara', 'Lucky Star', 31, 120),
('Route 13', 'Red', 'Hawksbay', 'Tower', 20, 120);

--for ev bus
INSERT INTO bus_routes (route_number, route_type, start_point, end_point, route_length_km, fare)
VALUES ('EV 1', 'EV', 'Malir Cantt', 'Dolmen Mall Clifton', 28, 120),
('EV 2', 'EV', 'Bahria Town', 'Malir Halt', 30, 120),
('EV 3', 'EV', 'Malir Cantt Check Post 5', 'Numaish', 20, 120),
('EV 4', 'EV', 'Bahria Town', 'Ayesha Manzil', 34, 120),
('EV 5', 'EV', 'DHA City', 'Sohrab Goth', 41, 120);

--for pink bus
INSERT INTO bus_routes (route_number, route_type, start_point, end_point, route_length_km, fare)
VALUES ('P Route 1', 'Pink', 'Model Colony', 'Tower', 28, 50),
('P Route 2', 'Pink', 'North Karachi', 'Korangi', 28, 50),
('P Route 10', 'Pink', 'Numaish Chowrangi', 'Seaview Beach', 28, 50),
('P Route 3', 'Pink', 'Powerhouse Chowrangi, North Karachi', 'Nasir Jump, Korangi', 28, 50),
('P Route 9', 'Pink', 'Al-Khidmat Hospital, Gulshan e Hadeed', 'Tower via Shahra e Faisal', 28, 50);  -- the km of each route is just a random value for pink (as it was not specified)

-- for green line bus
INSERT INTO bus_routes (route_number, route_type, start_point, end_point, route_length_km, fare)
VALUES ('G Route 1', 'Green', 'Karachi City Station', 'Surjani Terminal', 21, 55);

------------inserting values in bus_stops--------------

--Route 1:
INSERT INTO bus_stops (stop_name)
VALUES 
('khokrapar'),
('saudabd'),
('rcd ground'),
('kalaboard'),
('malir halt'),
('colony gate'),
('nata khan bridge'),
('drigh road station'),
('paf base faisal'),
('laal kothi'),
('karsaz'),
('nursery'),
('ftc'),
('regent plaza'),
('metropole'),
('fawwara chowk'),
('arts council'),
('shaheen complex'),
('i i chundrigar'),
('tower'),
('fisheries'),
('dockyard');

--Route 2:
INSERT INTO bus_stops (stop_name)
VALUES 
('power house'),
('up more'),
('nagan chowrangi'),
('shafiq morr'),
('sohrab goth'),
('gulshan chowrangi'),
('nipa'),
('johar morr'),
('cod'),
('shah faisal colony'),
('singer chowrangi'),
('khaddi stop'),
('indus hospital');

--Route 3:
INSERT INTO bus_stops (stop_name)
VALUES 
('sakhi hasan'),
('5 star chowrangi'),
('kda chowrangi'),
('board office'),
('nazimabad eid gah ground'),
('liaquatabad 10 number'),
('essa nagri'),
('civic centre'),
('national stadium'),
('korangi road'),
('kpt interchange upto shan chowrangi'),
('nasir jump');

--Route 4:
INSERT INTO bus_stops (stop_name)
VALUES 
('water pump'),
('ayesha manzil'),
('karimabad'),
('laloo khait'),
('teen hati'),
('jehangir road'),
('numaish'),
('mobile market'),
('urdu bazar'),
('civil hospital'),
('city court'),
('light house'),
('bolton market'),
('keamari');

--Route 8:
INSERT INTO bus_stops (stop_name)
VALUES 
('yousuf goth'),
('naval colony'),
('baldia'),
('sher shah'),
('gulbai'),
('agra taj colony'),
('daryabad'),
('jinnah bridge');

--Route 9:
INSERT INTO bus_stops (stop_name)
VALUES 
('gulshan e hadeed'),
('salah uddin ayubi road'),
('allah wali chowrangi'),
('national highway 5'),
('steel mill more'),
('port bin qasim more'),
('razzakabad abdullah goth'),
('chowkundi more'),
('fast university'),
('bhains colony more'),
('manzil pump'),
('quaidabad'),
('murghi khana'),
('prince aly boys school'),
('nadra center malir'),
('malir session court'),
('malir 15');

--Route 10:
INSERT INTO bus_stops (stop_name)
VALUES 
('numaish chowrangi'),
('frere hall'),
('teen talwar'),
('do talwar abdullah shah ghazi'),
('dolmen mall clifton'),
('clock tower dha'),
('26 street'),
('masjid e ayesha'),
('rahat park'),
('kpt interchange'),
('korangi crossing'),
('cbm university'),
('parco'),
('ibrahim hyderi');

--Route 11:
INSERT INTO bus_stops (stop_name)
VALUES 
('miran nakka'),
('gulistan colony'),
('bihar colony'),
('bahria complex'),
('m t khan road'),
('picd'),
('bahria complex 3'),
('khadda market'),
('abdullah shah ghazi'),
('bilawal chowrangi'),
('ziauddin hospital'),
('shireen jinnah colony');

--Route 12:
INSERT INTO bus_stops (stop_name)
VALUES 
('naddi kinara'),
('saudabad chowrangi'),
('malir mandir'),
('dawood chowrangi'),
('babar market'),
('landhi road'),
('qayyumabad'),
('defence mor'),
('national medical center'),
('gora qabristan'),
('jutt land'),
('lines area'),
('army public school'),
('lucky star saddar');

--Route 13:
INSERT INTO bus_stops (stop_name)
VALUES 
('hawksbay'),
('mauripur');

--EV 1:
INSERT INTO bus_stops (stop_name)
VALUES 
('cmh malir cantt'),
('tank chowk'),
('model colony mor'),
('jinnah ave'),
('airport'),
('dha phase 1');

--EV 2:
INSERT INTO bus_stops (stop_name)
VALUES 
('bahria town'),
('dumba goth'),
('toll plaza'),
('baqai university'),
('malir cantt gate 5'),
('malir cantt gate 6'),
('model mor');

--EV 3:
INSERT INTO bus_stops (stop_name)
VALUES 
('malir cantt check post 5'),
('rim jhim tower'),
('safoora chowrangi'),
('mausamiyat chowrangi'),
('kamran chowrangi'),
('darul sehat hospital'),
('johar chowrangi'),
('millennium mall'),
('dalmia road'),
('bahria university'),
('aga khan hospital'),
('liaquat national hospital'),
('pib colony'),
('jail chowrangi'),
('dawood engineering university'),
('islamia college'),
('people secretariat chowrangi');

--EV 4:
INSERT INTO bus_stops (stop_name)
VALUES 
('m9 toll plaza'),
('jamali pull'),
('new sabzi mandi'),
('al asif');

--EV 5:
INSERT INTO bus_stops (stop_name)
VALUES 
('dha city');

--Green Bus:
ALTER TABLE bus_stops
ADD CONSTRAINT bus_stops_stop_name_unique UNIQUE (stop_name); --This guarantees no duplicate stop names ever

INSERT INTO bus_stops (stop_name) VALUES
('surjani terminal'),
('4k chowrangi'),
('north karachi'),
('nagan chowrangi'),
('sakhi hassan'),
('shahrah-e-jehangir'),
('hyderi'),
('shahrah-e-humayun'),
('orange line'),
('north nazimabad'),
('eid gah bagh'),
('urdu bazaar'),
('gul bahar'),
('lasbela'),
('guru mandir'),
('numaish chowrangi'),
('agha khan iii road'),
('aurangzeb market'),
('merewether tower'),
('karachi port trust'),
('karachi city station')
ON CONFLICT (stop_name) DO NOTHING;

UPDATE bus_stops
SET latitude = 25.03186320446349,
    longitude = 67.06948410337029
WHERE stop_name = 'surjani terminal';

UPDATE bus_stops
SET latitude = 24.932032406615694,
    longitude = 67.05991884387504
WHERE stop_name = 'shahrah-e-jehangir';


--------inserting order of transfer stops for each route----------

-- Route 1 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order) VALUES
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'khokrapar'), 1),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'saudabd'), 2),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'rcd ground'), 3),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kalaboard'), 4),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir halt'), 5),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'colony gate'), 6),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nata khan bridge'), 7),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'drigh road station'), 8),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'paf base faisal'), 9),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'laal kothi'), 10),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karsaz'), 11),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nursery'), 12),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ftc'), 13),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'regent plaza'), 14),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'metropole'), 15),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'fawwara chowk'), 16),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'arts council'), 17),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shaheen complex'), 18),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'i i chundrigar'), 19),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tower'), 20),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'fisheries'), 21),
(1, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dockyard'), 22);

-- Route 2 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order) VALUES
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'power house'), 1),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'up more'), 2),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nagan chowrangi'), 3),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shafiq morr'), 4),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sohrab goth'), 5),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gulshan chowrangi'), 6),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nipa'), 7),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'johar morr'), 8),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'cod'), 9),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'drigh road station'), 10),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'colony gate'), 11),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shah faisal colony'), 12),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'singer chowrangi'), 13),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'khaddi stop'), 14),
(2, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'indus hospital'), 15);

-- Route 3 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order) VALUES
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'power house'), 1),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'up more'), 2),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nagan chowrangi'), 3),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sakhi hasan'), 4),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = '5 star chowrangi'), 5),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kda chowrangi'), 6),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'board office'), 7),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nazimabad eid gah ground'), 8),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'liaquatabad 10 number'), 9),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'essa nagri'), 10),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'civic centre'), 11),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'national stadium'), 12),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karsaz'), 13),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nursery'), 14),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ftc'), 15),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'korangi road'), 16),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kpt interchange upto shan chowrangi'), 17),
(3, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nasir jump'), 18);

-- Route 4 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order) VALUES
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'power house'), 1),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'up more'), 2),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nagan chowrangi'), 3),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shafiq morr'), 4),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sohrab goth'), 5),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'water pump'), 6),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ayesha manzil'), 7),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karimabad'), 8),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'liaquatabad 10 number'), 9),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'laloo khait'), 10),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'teen hati'), 11),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jehangir road'), 12),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'numaish'), 13),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'mobile market'), 14),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'urdu bazar'), 15),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'civil hospital'), 16),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'city court'), 17),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'light house'), 18),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bolton market'), 19),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tower'), 20),
(4, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'keamari'), 21);

-- Route 8 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'yousuf goth'), 1),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'naval colony'), 2),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'baldia'), 3),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sher shah'), 4),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gulbai'), 5),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'agra taj colony'), 6),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'daryabad'), 7),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jinnah bridge'), 8),
(5, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tower'), 9);

-- Route 9 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gulshan e hadeed'), 1),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'salah uddin ayubi road'), 2),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'allah wali chowrangi'), 3),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'national highway 5'), 4),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'steel mill more'), 5),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'port bin qasim more'), 6),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'razzakabad abdullah goth'), 7),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'chowkundi more'), 8),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'fast university'), 9),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bhains colony more'), 10),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'manzil pump'), 11),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'quaidabad'), 12),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'murghi khana'), 13),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'prince aly boys school'), 14),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nadra center malir'), 15),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir session court'), 16),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir 15'), 17),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kalaboard'), 18),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir halt'), 19),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'colony gate'), 20),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nata khan bridge'), 21),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'drigh road station'), 22),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'paf base faisal'), 23),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'laal kothi'), 24),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karsaz'), 25),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nursery'), 26),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ftc'), 27),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'regent plaza'), 28),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'metropole'), 29),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'fawwara chowk'), 30),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'arts council'), 31),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shaheen complex'), 32),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'i i chundrigar'), 33),
(6, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tower'), 34);

-- Route 10 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'numaish chowrangi'), 1),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'mobile market'), 2),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'metropole'), 3),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'frere hall'), 4),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'teen talwar'), 5),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'do talwar abdullah shah ghazi'), 6),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dolmen mall clifton'), 7),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'clock tower dha'), 8),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = '26 street'), 9),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'masjid e ayesha'), 10),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'rahat park'), 11),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kpt interchange'), 12),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'korangi crossing'), 13),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'cbm university'), 14),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'parco'), 15),
(7, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ibrahim hyderi'), 16);

-- Route 11 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'miran nakka'), 1),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gulistan colony'), 2),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bihar colony'), 3),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'agra taj colony'), 4),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'daryabad'), 5),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jinnah bridge'), 6),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bahria complex'), 7),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'm t khan road'), 8),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'picd'), 9),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bahria complex 3'), 10),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'khadda market'), 11),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'abdullah shah ghazi'), 12),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bilawal chowrangi'), 13),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ziauddin hospital'), 14),
(8, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shireen jinnah colony'), 15);

-- Route 12 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'naddi kinara'), 1),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'khokrapar'), 2),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'saudabad chowrangi'), 3),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'rcd ground'), 4),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kalaboard'), 5),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir 15'), 6),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir mandir'), 7),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir session court'), 8),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'murghi khana'), 9),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'quaidabad'), 10),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dawood chowrangi'), 11),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'babar market'), 12),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'landhi road'), 13),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nasir jump'), 14),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'indus hospital'), 15),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'korangi crossing'), 16),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'qayyumabad'), 17),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'defence mor'), 18),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'national medical center'), 19),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gora qabristan'), 20),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ftc'), 21),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jutt land'), 22),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'lines area'), 23),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'army public school'), 24),
(9, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'lucky star saddar'), 25);

-- Route 13 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'hawksbay'), 1),
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'mauripur'), 2),
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gulbai'), 3),
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'agra taj colony'), 4),
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'daryabad'), 5),
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jinnah bridge'), 6),
(10, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tower'), 7);

-- EV 1 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'cmh malir cantt'), 1),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tank chowk'), 2),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'model colony mor'), 3),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jinnah ave'), 4),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'airport'), 5),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'colony gate'), 6),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nata khan bridge'), 7),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'drigh road station'), 8),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'paf base faisal'), 9),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'laal kothi'), 10),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karsaz'), 11),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nursery'), 12),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ftc'), 13),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'korangi road'), 14),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dha phase 1'), 15),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'masjid e ayesha'), 16),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'clock tower dha'), 17),
(11, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dolmen mall clifton'), 18);

-- EV 2 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bahria town'), 1),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dumba goth'), 2),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'toll plaza'), 3),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'baqai university'), 4),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir cantt gate 5'), 5),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir cantt gate 6'), 6),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'tank chowk'), 7),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'model mor'), 8),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jinnah ave'), 9),
(12, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir halt'), 10);

-- EV 3 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'malir cantt check post 5'), 1),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'rim jhim tower'), 2),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'safoora chowrangi'), 3),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'mausamiyat chowrangi'), 4),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'kamran chowrangi'), 5),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'darul sehat hospital'), 6),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'johar chowrangi'), 7),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'johar morr'), 8),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'millennium mall'), 9),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dalmia road'), 10),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bahria university'), 11),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'national stadium'), 12),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'aga khan hospital'), 13),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'liaquat national hospital'), 14),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'pib colony'), 15),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jail chowrangi'), 16),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dawood engineering university'), 17),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'islamia college'), 18),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'people secretariat chowrangi'), 19),
(13, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'numaish'), 20);

-- EV 4 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bahria town'), 1),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dumba goth'), 2),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'm9 toll plaza'), 3),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jamali pull'), 4),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'new sabzi mandi'), 5),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'al asif'), 6),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sohrab goth'), 7),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'water pump'), 8),
(14, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'ayesha manzil'), 9);

-- EV 5 stop order
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dha city'), 1),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'bahria town'), 2),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'dumba goth'), 3),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'm9 toll plaza'), 4),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'jamali pull'), 5),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'new sabzi mandi'), 6),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'al asif'), 7),
(15, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sohrab goth'), 8);

-- Green Line stop order:
INSERT INTO transfer_stops (route_id, stop_id, stop_order)
VALUES
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karachi city station'), 1),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'karachi port trust'), 2),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'merewether tower'), 3),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'aurangzeb market'), 4),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'agha khan iii road'), 5),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'numaish chowrangi'), 6),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'guru mandir'), 7),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'lasbela'), 8),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'gul bahar'), 9),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'urdu bazaar'), 10),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'eid gah bagh'), 11),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'north nazimabad'), 12),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'orange line'), 13),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shahrah-e-humayun'), 14),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'hyderi'), 15),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'shahrah-e-jehangir'), 16),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'sakhi hassan'), 17),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'nagan chowrangi'), 18),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'up more'), 19),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'north karachi'), 20),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = '4k chowrangi'), 21),
(16, (SELECT stop_id FROM bus_stops WHERE LOWER(stop_name) = 'surjani terminal'), 22);

DELETE FROM transfer_stops
WHERE route_id = 16
  AND stop_id IN (
    SELECT stop_id FROM bus_stops
    WHERE LOWER(stop_name) IN (
      'karachi city station',
      'karachi port trust',
      'merewether tower',
      'aurangzeb market',
      'agha khan iii road',
      'numaish chowrangi',
      'guru mandir',
      'lasbela',
      'gul bahar',
      'urdu bazaar',
      'eid gah bagh',
      'north nazimabad',
      'orange line',
      'shahrah-e-humayun',
      'hyderi',
      'shahrah-e-jehangir',
      'sakhi hassan',
      'nagan chowrangi',
      'up more',
      'north karachi',
      '4k chowrangi',
      'surjani terminal'
    )
  );
--adding coordinates manually
UPDATE bus_stops SET latitude = 24.919756400506593, longitude = 67.19378775156216 WHERE stop_name = 'saudabd';
UPDATE bus_stops SET latitude = 24.86588737545942, longitude = 67.06955402613076 WHERE stop_name = 'laal kothi';
UPDATE bus_stops SET latitude = 24.88204112274426, longitude = 67.0205233522844 WHERE stop_name = 'fawwara chowk';
UPDATE bus_stops SET latitude = 24.980296501596627, longitude = 67.06632660715071 WHERE stop_name = 'up more';
UPDATE bus_stops SET latitude = 24.958064445877845, longitude = 67.07606498466288 WHERE stop_name = 'shafiq morr';
UPDATE bus_stops SET latitude = 24.911670009140703, longitude = 67.11461160879486 WHERE stop_name = 'johar morr';
UPDATE bus_stops SET latitude = 24.843500894567445, longitude = 67.16207107686826 WHERE stop_name = 'khaddi stop';
UPDATE bus_stops SET latitude = 24.915054661496505, longitude = 67.04864027854845 WHERE stop_name = 'liaquatabad 10 number';
UPDATE bus_stops SET latitude = 24.902839604657522, longitude = 67.07198219215199 WHERE stop_name = 'civic centre';
UPDATE bus_stops SET latitude = 24.850403338034056, longitude = 67.20829849748023 WHERE stop_name = 'kpt interchange upto shan chowrangi';
UPDATE bus_stops SET latitude = 24.896329895681568, longitude = 67.04346873958565 WHERE stop_name = 'teen hati';
UPDATE bus_stops SET latitude = 24.846416168881227, longitude = 67.13011276456484 WHERE stop_name = 'salah uddin ayubi road';
UPDATE bus_stops SET latitude = 24.866829946812338, longitude = 67.32718691024952 WHERE stop_name = 'steel mill more';
UPDATE bus_stops SET latitude = 24.77871143061884, longitude = 67.33513865387799 WHERE stop_name = 'port bin qasim more';
UPDATE bus_stops SET latitude = 24.863714982817616, longitude = 67.25748154895646 WHERE stop_name = 'bhains colony more';
UPDATE bus_stops SET latitude = 24.861222955115153, longitude = 67.2288023162864 WHERE stop_name = 'manzil pump';
UPDATE bus_stops SET latitude = 24.86620696029222, longitude = 67.21016334758522 WHERE stop_name = 'murghi khana';
UPDATE bus_stops SET latitude = 24.868688307554862, longitude = 67.20188003212468 WHERE stop_name = 'prince aly boys school';
UPDATE bus_stops SET latitude = 24.87128486622645, longitude = 67.19798173176534 WHERE stop_name = 'nadra center malir';

UPDATE bus_stops SET latitude = 24.87403011671741, longitude = 67.19440515078492 WHERE stop_name = 'malir session court';
UPDATE bus_stops SET latitude = 24.878859648356322, longitude = 66.99433297750316 WHERE stop_name = 'miran nakka';
UPDATE bus_stops SET latitude = 24.860970206841927, longitude = 67.02117406819256 WHERE stop_name = 'picd';
UPDATE bus_stops SET latitude = 24.815909814081074, longitude = 67.02030858821631 WHERE stop_name = 'bilawal chowrangi';
UPDATE bus_stops SET latitude = 24.821203357219375, longitude = 67.03416656797788 WHERE stop_name = 'do talwar abdullah shah ghazi';
UPDATE bus_stops SET latitude = 24.778491135438426, longitude = 67.05422711030467 WHERE stop_name = 'clock tower dha';
UPDATE bus_stops SET latitude = 24.812470884877005, longitude = 67.11716098147296 WHERE stop_name = 'cbm university';
UPDATE bus_stops SET latitude = 24.913514748310096, longitude = 67.21402646172092 WHERE stop_name = 'naddi kinara';
UPDATE bus_stops SET latitude = 24.864860243959445, longitude = 67.03820823130876 WHERE stop_name = 'jutt land';
UPDATE bus_stops SET latitude = 24.94881772076352, longitude = 67.21460939681837 WHERE stop_name = 'cmh malir cantt';
UPDATE bus_stops SET latitude = 24.90284637095927, longitude = 67.18620944733472 WHERE stop_name = 'model colony mor';
UPDATE bus_stops SET latitude = 24.925045857767792, longitude = 67.20241409496626 WHERE stop_name = 'malir cantt gate 6';
UPDATE bus_stops SET latitude = 24.903634603897462, longitude = 67.18196082831876 WHERE stop_name = 'model mor';
UPDATE bus_stops SET latitude = 24.947749716527273, longitude = 67.18292475078759 WHERE stop_name = 'malir cantt check post 5';
UPDATE bus_stops SET latitude = 24.939534532499195, longitude = 67.1562766409976 WHERE stop_name = 'safoora chowrangi';
UPDATE bus_stops SET latitude = 24.935871107228596, longitude = 67.13828969618649 WHERE stop_name = 'mausamiyat chowrangi';
UPDATE bus_stops SET latitude = 24.98311802701404, longitude = 67.22744664706505 WHERE stop_name = 'm9 toll plaza';
UPDATE bus_stops SET latitude = 24.97335764920069, longitude = 67.11844074049571 WHERE stop_name = 'jamali pull';
UPDATE bus_stops SET latitude = 24.996112808670777, longitude = 67.15760601010496 WHERE stop_name = 'new sabzi mandi';


-- creating extension
CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- Optional: keep things organized
CREATE SCHEMA IF NOT EXISTS smart_transit;

-- =========================
-- STOPS (from graph_nodes.csv)
-- columns: stop_id, stop_name, lat, lon
-- =========================
CREATE TABLE IF NOT EXISTS smart_transit.stops (
  stop_id     INTEGER PRIMARY KEY,
  stop_name   TEXT NOT NULL,
  lat         DOUBLE PRECISION NOT NULL,
  lon         DOUBLE PRECISION NOT NULL
);

-- Helpful indexes (search + nearest stop queries later)
CREATE INDEX IF NOT EXISTS idx_stops_name_trgm
  ON smart_transit.stops USING GIN (stop_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_stops_lat_lon
  ON smart_transit.stops (lat, lon);

-- Enable trigram index support (for the stop_name index above)
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- =========================
-- ROUTES / LINES (derived from edges.csv)
-- edges.csv has: route_id, line_name
-- =========================
CREATE TABLE IF NOT EXISTS smart_transit.routes (
  route_id   INTEGER PRIMARY KEY,
  line_name  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_routes_line_name
  ON smart_transit.routes (line_name);


-- =========================
-- EDGES (from graph_edges.csv)
-- columns: u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only
-- We store line_name too (denormalized) so your import is 1:1 with the CSV.
-- Later you can rely on routes.line_name as the source of truth if you want.
-- =========================
CREATE TABLE IF NOT EXISTS smart_transit.edges (
  edge_id      BIGSERIAL PRIMARY KEY,

  u_stop_id    INTEGER NOT NULL,
  v_stop_id    INTEGER NOT NULL,

  route_id     INTEGER NOT NULL,
  line_name    TEXT NOT NULL,

  distance_km  DOUBLE PRECISION NOT NULL CHECK (distance_km >= 0),
  time_min     DOUBLE PRECISION NOT NULL CHECK (time_min >= 0),
  female_only  BOOLEAN NOT NULL,

  CONSTRAINT fk_edges_u_stop
    FOREIGN KEY (u_stop_id) REFERENCES smart_transit.stops(stop_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,

  CONSTRAINT fk_edges_v_stop
    FOREIGN KEY (v_stop_id) REFERENCES smart_transit.stops(stop_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,

  CONSTRAINT fk_edges_route
    FOREIGN KEY (route_id) REFERENCES smart_transit.routes(route_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,

  CONSTRAINT chk_no_self_loop
    CHECK (u_stop_id <> v_stop_id)
);

-- Indexes for routing lookups
CREATE INDEX IF NOT EXISTS idx_edges_u ON smart_transit.edges (u_stop_id);
CREATE INDEX IF NOT EXISTS idx_edges_v ON smart_transit.edges (v_stop_id);
CREATE INDEX IF NOT EXISTS idx_edges_route ON smart_transit.edges (route_id);
CREATE INDEX IF NOT EXISTS idx_edges_line_name ON smart_transit.edges (line_name);

-- Optional: prevent exact duplicates (same route + same endpoints + same metrics)
-- If your CSV contains duplicates intentionally, skip this constraint.
CREATE UNIQUE INDEX IF NOT EXISTS uq_edges_route_uv_metrics
  ON smart_transit.edges (route_id, u_stop_id, v_stop_id, distance_km, time_min, female_only);


CREATE TABLE smart_transit.edges_staging (
  u_stop_id    INTEGER,
  v_stop_id    INTEGER,
  route_id     INTEGER,
  line_name    TEXT,
  distance_km  DOUBLE PRECISION,
  time_min     DOUBLE PRECISION,
  female_only  BOOLEAN
);

select *from smart_transit.stops
COPY smart_transit.stops (stop_id, stop_name, lat, lon)
FROM 'C:\Users\ayubs\OneDrive\Desktop\db-fyp\graphdata\graph_nodes.csv'
WITH (FORMAT csv, HEADER true);

COPY smart_transit.edges_staging (u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only)
FROM 'C:\Users\ayubs\OneDrive\Desktop\db-fyp\graphdata/graph_edges.csv'
WITH (FORMAT csv, HEADER true);

INSERT INTO smart_transit.routes (route_id, line_name)
SELECT DISTINCT route_id, line_name
FROM smart_transit.edges_staging
ON CONFLICT (route_id) DO UPDATE
SET line_name = EXCLUDED.line_name;

INSERT INTO smart_transit.routes (route_id, line_name)
SELECT DISTINCT route_id, line_name
FROM smart_transit.edges_staging
WHERE route_id IS NOT NULL
ON CONFLICT (route_id) DO UPDATE
SET line_name = EXCLUDED.line_name;

INSERT INTO smart_transit.edges (u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only)
SELECT u_stop_id, v_stop_id, route_id, line_name, distance_km, time_min, female_only
FROM smart_transit.edges_staging;

SELECT
  table_schema,
  table_name,
  ordinal_position,
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_schema = 'smart_transit'
  AND table_name IN ('stops', 'routes', 'edges')
ORDER BY table_name, ordinal_position;

SELECT 'stops' AS table_name, COUNT(*) AS rows FROM smart_transit.stops
UNION ALL
SELECT 'routes', COUNT(*) FROM smart_transit.routes
UNION ALL
SELECT 'edges', COUNT(*) FROM smart_transit.edges;

SELECT * FROM smart_transit.stops ORDER BY stop_id LIMIT 10;

SELECT
  e.edge_id,
  e.route_id,
  e.line_name,
  e.u_stop_id,
  su.stop_name AS u_stop_name,
  e.v_stop_id,
  sv.stop_name AS v_stop_name,
  e.distance_km,
  e.time_min,
  e.female_only
FROM smart_transit.edges e
JOIN smart_transit.stops su ON su.stop_id = e.u_stop_id
JOIN smart_transit.stops sv ON sv.stop_id = e.v_stop_id
ORDER BY e.edge_id
LIMIT 20;

--1st query for adding 2 new double decker stops 
WITH next_ids AS (
  SELECT
    COALESCE(MAX(stop_id), 0) + 1 AS baloch_id,
    COALESCE(MAX(stop_id), 0) + 2 AS zainab_id
  FROM smart_transit.stops
)
INSERT INTO smart_transit.stops (stop_id, stop_name, lat, lon)
SELECT baloch_id, 'baloch colony', 24.948237314849955, 67.02314339283444 FROM next_ids
UNION ALL
SELECT zainab_id, 'zainab market', 24.85562025621321, 67.02840632584234 FROM next_ids
ON CONFLICT (stop_id) DO NOTHING;

-- 2nd for adding new route 
INSERT INTO smart_transit.routes (route_id, line_name)
VALUES (22, 'Double Decker')
ON CONFLICT (route_id) DO UPDATE
SET line_name = EXCLUDED.line_name;

-- python script doulbledeckerroute.py
SELECT stop_id, stop_name
FROM smart_transit.stops
WHERE lower(stop_name) IN ('zainab market', 'baloch colony');

SELECT stop_id, stop_name, lat, lon
FROM smart_transit.stops
WHERE lower(stop_name) LIKE '%zainab%'
   OR lower(stop_name) LIKE '%baloch%';

-- confirm route exists
SELECT * FROM smart_transit.routes WHERE route_id = 22;

-- confirm new edges exist + female_only is false
SELECT edge_id, u_stop_id, v_stop_id, route_id, line_name, female_only
FROM smart_transit.edges
WHERE route_id = 22
ORDER BY edge_id;

-- confirm the two new stops exist
SELECT stop_id, stop_name, lat, lon
FROM smart_transit.stops
WHERE stop_id IN (195,196);

SELECT COUNT(*) FROM smart_transit.edges WHERE u_stop_id = 170 OR v_stop_id = 170;

SELECT 
    s.stop_id,
    s.stop_name
FROM smart_transit.stops s
LEFT JOIN smart_transit.edges e
    ON s.stop_id = e.u_stop_id
    OR s.stop_id = e.v_stop_id
WHERE e.u_stop_id IS NULL
ORDER BY s.stop_id;
SELECT DISTINCT
    s.stop_id,
    s.stop_name
    
FROM smart_transit.stops s
LEFT JOIN smart_transit.edges e
    ON s.stop_id = e.u_stop_id
    OR s.stop_id = e.v_stop_id
WHERE e.line_name ='Green'
ORDER BY s.stop_id;
--for route id
SELECT DISTINCT route_id, line_name
FROM smart_transit.edges
WHERE lower(line_name) = 'green'
ORDER BY route_id;
-- for latest stops id
SELECT MAX(stop_id) AS max_stop_id FROM smart_transit.stops;
-- then manually inset max stop ids
INSERT INTO smart_transit.stops (stop_id, stop_name, lat, lon)
VALUES
  (197, 'nagan chowrangi', 24.965766856621283, 67.0670336103113),
  (198, 'up morr',         24.973043422097206, 67.06668912195252),
  (199, 'north karachi',   24.975981494625245, 67.06622496797742);

--  confirming stops exist
SELECT stop_id, stop_name
FROM smart_transit.stops
WHERE stop_id IN (172,171,170,169,168,165,164)
ORDER BY stop_id;

-- confirming no edges 
SELECT s.stop_id, s.stop_name, COUNT(e.*) AS edge_count
FROM smart_transit.stops s
LEFT JOIN smart_transit.edges e
  ON s.stop_id = e.u_stop_id OR s.stop_id = e.v_stop_id
WHERE s.stop_id IN (164,165,168,169,170,197,198,199)
GROUP BY s.stop_id, s.stop_name
ORDER BY s.stop_id;

--checking green again
SELECT u_stop_id, v_stop_id, distance_km, time_min
FROM smart_transit.edges
WHERE route_id = 21
ORDER BY u_stop_id;


SELECT
    stop_name,
    COUNT(*) AS count,
    ARRAY_AGG(stop_id ORDER BY stop_id) AS stop_ids
FROM smart_transit.stops
WHERE lower(stop_name) LIKE '%up morr%'
   OR lower(stop_name) LIKE '%nagan%'
GROUP BY stop_name
HAVING COUNT(*) > 1
ORDER BY stop_name;

SELECT
    lower(stop_name) AS normalized_name,
    COUNT(*) AS count,
    ARRAY_AGG(stop_id ORDER BY stop_id) AS stop_ids
FROM smart_transit.stops
GROUP BY lower(stop_name)
HAVING COUNT(*) > 1
ORDER BY count DESC;

select *
FROM smart_transit.edges
where u_stop_id = 199 or v_stop_id = 199;

update smart_transit.edges
set u_stop_id=166
where u_stop_id=199;

update smart_transit.edges
set v_stop_id =166
where v_stop_id=199;

select *
FROM smart_transit.edges
where u_stop_id = 198 or v_stop_id = 198;

update smart_transit.edges
set u_stop_id=166
where u_stop_id=199;

update smart_transit.edges
set v_stop_id =166
where v_stop_id=199;

BEGIN;

-- ------------------------------------------------------------
-- 0) OPTIONAL: Preview current usage (sanity check)
-- ------------------------------------------------------------
SELECT 'nagan-before' AS tag, COUNT(*) AS edge_refs
FROM smart_transit.edges
WHERE u_stop_id = 197 OR v_stop_id = 197;

SELECT 'northk-before' AS tag, COUNT(*) AS edge_refs
FROM smart_transit.edges
WHERE u_stop_id = 199 OR v_stop_id = 199;

-- ------------------------------------------------------------
-- 1) Rewire EDGES: nagan chowrangi (197 -> 25)
-- ------------------------------------------------------------
UPDATE smart_transit.edges
SET u_stop_id = 25
WHERE u_stop_id = 197;

UPDATE smart_transit.edges
SET v_stop_id = 25
WHERE v_stop_id = 197;

-- ------------------------------------------------------------
-- 2) Rewire EDGES: north karachi (199 -> 166)
-- ------------------------------------------------------------
UPDATE smart_transit.edges
SET u_stop_id = 166
WHERE u_stop_id = 199;

UPDATE smart_transit.edges
SET v_stop_id = 166
WHERE v_stop_id = 199;

-- ------------------------------------------------------------
-- 3) (IMPORTANT) Remove potential duplicate edges created by rewiring
-- If you have no unique constraint, duplicates can exist now.
-- This keeps the "first" row and deletes the rest for identical tuples.
-- ------------------------------------------------------------
DELETE FROM smart_transit.edges e
USING smart_transit.edges d
WHERE e.ctid < d.ctid
  AND e.u_stop_id = d.u_stop_id
  AND e.v_stop_id = d.v_stop_id
  AND e.route_id  = d.route_id;

-- ------------------------------------------------------------
-- 4) Delete the duplicate STOPS (only after rewiring edges)
-- ------------------------------------------------------------
DELETE FROM smart_transit.stops WHERE stop_id = 197;
DELETE FROM smart_transit.stops WHERE stop_id = 199;

-- ------------------------------------------------------------
-- 5) Verify: removed IDs no longer appear anywhere in edges
-- ------------------------------------------------------------
SELECT 'nagan-after' AS tag, COUNT(*) AS edge_refs
FROM smart_transit.edges
WHERE u_stop_id = 197 OR v_stop_id = 197;

SELECT 'northk-after' AS tag, COUNT(*) AS edge_refs
FROM smart_transit.edges
WHERE u_stop_id = 199 OR v_stop_id = 199;

COMMIT;
