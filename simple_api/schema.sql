drop table if exists employees;
create table employees (
  id integer primary key autoincrement,
  name text not null,
  department text not null,
  salary numeric not null
);