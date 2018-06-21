drop table if exists foods;
create table foods (
  id integer primary key autoincrement,
  name text not null,
  food_type text not null
);