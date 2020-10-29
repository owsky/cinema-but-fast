from flask_login import current_user
from sqlalchemy import text, create_engine
from classes import InsufficientBalanceException, Projection, User

engine = create_engine('postgresql://cinema_user:cinema_password@localhost:5432/cinema_database')


def purchase(proj_id, selected_seats):
    with engine.begin() as connection:
        s1 = text("SELECT users_balance FROM public.users WHERE users_id = :e1")
        rs1 = connection.execute(s1, e1=current_user.id)
        balance = rs1.fetchone()

        s2 = text("SELECT projections_price FROM public.projections WHERE projections_id = :e2")
        rs2 = connection.execute(s2, e2=proj_id)
        tprice = rs2.fetchone()
        total = balance.users_balance - (tprice.projections_price * len(selected_seats))
        if total < 0:
            raise InsufficientBalanceException(balance.users_balance)
        for x in selected_seats:
            s = text(
                "INSERT INTO public.tickets(tickets_user, tickets_projection, tickets_seat) VALUES (:e1, :e2, :e3)")
            connection.execute(s, e1=current_user.id, e2=proj_id, e3=x)
        s = text("UPDATE public.users SET users_balance = :e1 WHERE users_id = :e2")
        connection.execute(s, e1=total, e2=current_user.id)
    return


def format_projections(proj):
    proj_list = list()
    for p in proj:
        proj_date = p.projections_date_time.strftime("%m/%d/%Y")
        proj_hour = p.projections_date_time.strftime("%H:%M:%S")[:5]
        proj_list.append(
            Projection(p.projections_id, proj_date, proj_hour, p.rooms_name, p.projections_price,
                       how_many_seats_left(p[0])))
    return proj_list


# ritorna un array di possibili scelte
def get_gender():
    conn = engine.connect()
    s = text("SELECT unnest(enum_range(NULL::public.gender)) AS gender")
    rs = conn.execute(s)
    gen = rs.fetchall()
    return gen


def get_genres():
    conn = engine.connect()
    s = text("SELECT unnest(enum_range(NULL::public.genre)) AS genre")
    rs = conn.execute(s)
    gen = rs.fetchall()
    return gen


def get_orders(uid):
    conn = engine.connect()
    s = text("""SELECT movies_title, projections_date_time, rooms_name, seats_name FROM tickets
                JOIN seats ON seats_id=tickets_seat
                JOIN rooms ON rooms_id=seats_room
                JOIN projections ON tickets_projection=projections_id
                JOIN movies ON movies_id=projections_movie
                WHERE tickets_user=:e1""")
    rs = conn.execute(s, e1=uid)
    orders = rs.fetchall()
    return orders


# selezione degli attori (dal nome)
def get_actor_by_name(name):
    # se non viene specificato il valore name, ritorna tutta la lista 'actors' con tutti i suoi attributi
    if name is None:
        conn = engine.connect()
        s1 = text("SELECT * FROM actors")
        rs = conn.execute(s1)
        act = rs.fetchall()
    # altrimenti ritorna la riga della tabella 'actors' che soddisfa la condizione 'actors_fullname' = name
    else:
        conn = engine.connect()
        s = text("SELECT * FROM actors WHERE actors_fullname = :n")
        rs = conn.execute(s, n=name)
        act = rs.fetchone()
    conn.close()
    return act


# selezione degli attori (dall'id)
def get_actor_by_id(aid):
    # ritorna la riga della tabella actors che soddisfa la condizione 'actors_id' = aid
    conn = engine.connect()
    s = text("SELECT * FROM public.actors WHERE actors_id = :e")
    rs = conn.execute(s, e=aid)
    act = rs.fetchone()
    conn.close()
    return act


# selezione della sala (dal nome)
def get_rooms_by_name(name):
    conn = engine.connect()
    # seleziona la riga della tabella rooms che soddisfa la condizione 'rooms_name' = name
    if name:
        s = text("SELECT * FROM rooms WHERE rooms_name = :n")
        rs = conn.execute(s, n=name)
        rid = rs.fetchone()
    # se non viene specificato il valore name, ritorna tutta la lista 'rooms' con tutti i suoi attributi
    else:
        s = text("SELECT * FROM rooms")
        rs = conn.execute(s)
        rid = rs.fetchall()
    conn.close()
    return rid


# selezione della sala (dall'id)
def get_rooms_by_id(cod):
    conn = engine.connect()
    # seleziona la riga della tabella rooms che soddisfa la condizione 'rooms_id' = cod
    if cod:
        s = text("SELECT * FROM rooms WHERE rooms_id = :c")
        rs = conn.execute(s, c=cod)
        rid = rs.fetchone()
    # se non viene specificato il valore name, ritorna tutta la lista 'rooms' con tutti i suoi attributi
    else:
        s = text("SELECT * FROM rooms")
        rs = conn.execute(s)
        rid = rs.fetchall()
    conn.close()
    return rid


# check per l'inserimento di una proiezione
def check_time2(proj, start, end, room):
    conn = engine.connect()
    # controlla che l'orario 'start' e 'end' non siano in interferenza con altre proiezioni
    # seleziona le interferenze se sono presenti
    s = text("""SELECT projections_id FROM public.projections
                JOIN public.movies ON projections.projections_movie = movies.movies_id
                WHERE projections_room =:r AND projections_id<>:p AND projections_date_time >= :s
                AND (projections_date_time + (movies_duration * interval '1 minute'))<= :e""")
    rs = conn.execute(s, p=proj, r=room, s=start, e=end)
    ris = rs.fetchone()
    conn.close()
    return ris


# check per l'inserimento di una proiezione
def check_time(proj, start, end, room):
    conn = engine.connect()
    # controlla se ci siano altre proiezioni inclusa periodo di tempo tra 'start' e 'end' (= data di inizio e fine della proiezione da inserire)
    # seleziona le interferenze se sono presenti
    s = text("""SELECT projections_id FROM public.projections
                JOIN public.movies ON projections_movie=movies_id
                WHERE projections_room = :r AND projections_id <>:p AND
                (:st BETWEEN projections_date_time AND projections_date_time + (movies_duration * interval '1 minute') OR
                :e BETWEEN projections_date_time AND projections_date_time + (movies_duration * interval '1 minute'))""")
    rs = conn.execute(s, p=proj, r=room, st=start, e=end)
    ris = rs.fetchone()
    conn.close()
    return ris


def check_cast(movid, actid):
    conn = engine.connect()
    s = text("SELECT * FROM public.cast WHERE cast_actor=:a AND cast_movie=:m")
    rs = conn.execute(s, a=actid, m=movid)
    check = rs.fetchone()
    conn.close()
    return check


def get_directors_by_id(cod):
    conn = engine.connect()
    if cod:
        s = text("SELECT * FROM directors WHERE directors_id = :c")
        rs = conn.execute(s, c=cod)
        did = rs.fetchone()
    else:
        s = text("SELECT * FROM directors")
        rs = conn.execute(s)
        did = rs.fetchall()
    conn.close()
    return did


def get_directors_by_name(name):
    conn = engine.connect()
    if name:
        s = text("SELECT * FROM directors WHERE directors_name = :n")
        rs = conn.execute(s, n=name)
        did = rs.fetchone()
    else:
        s = text("SELECT * FROM directors")
        rs = conn.execute(s)
        did = rs.fetchall()
    conn.close()
    return did


# Functions
def user_by_email(user_email):
    conn = engine.connect()
    s = text("SELECT * FROM public.users WHERE users_email = :e1")
    rs = conn.execute(s, e1=user_email)
    u = rs.fetchone()
    conn.close()
    if u:
        return User(u.users_id, u.users_email, u.users_name, u.users_surname, u.users_pwd, u.users_is_manager,
                    u.users_balance)
    else:
        return None


def get_movies(mov):
    conn = engine.connect()
    if mov:
        s = text("""SELECT * FROM movies
                    JOIN directors ON movies.movies_director = directors.directors_id
                    WHERE movies_title = :e1""")
        rs = conn.execute(s, e1=mov)
        films = rs.fetchone()
    else:
        s = text("SELECT * FROM movies JOIN directors ON movies_director = directors_id")
        rs = conn.execute(s)
        films = rs.fetchall()
    conn.close()
    return films


def get_actors(mov):
    conn = engine.connect()
    if mov:
        s = text("""SELECT actors_fullname FROM movies
                    JOIN directors ON movies.movies_director = directors.directors_id
                    JOIN public.cast ON movies_id = public.cast.cast_movie
                    JOIN actors ON cast_actor = actors_id
                    WHERE movies_title = :e1""")
        rs = conn.execute(s, e1=mov)
    else:
        s = text("SELECT * FROM actors ORDER BY actors_id")
        rs = conn.execute(s)
    act = rs.fetchall()
    conn.close()
    return act


def get_last_movies():
    conn = engine.connect()
    s = text("SELECT * FROM movies JOIN directors ON movies_director = directors_id ORDER BY movies_id DESC LIMIT 5")
    rs = conn.execute(s)
    films = rs.fetchall()
    conn.close()
    return films


def get_projections(mov):
    conn = engine.connect()
    if mov:
        s = text("""SELECT projections_id, projections_date_time, projections_price, movies_title, movies_genre, movies_synopsis, movies_duration, directors_name, rooms_name,
                        (SELECT string_agg(actors_fullname::text, ', ') AS actors
                         FROM public.actors
                         JOIN public.cast ON cast_actor=actors_id
                         JOIN public.movies ON cast_movie=movies_id
                         WHERE movies_title=:e1)
                    FROM public.projections
                    JOIN public.movies ON projections_movie = movies_id
                    JOIN public.directors ON movies_director = directors_id
                    JOIN public.rooms ON projections_room = rooms_id 
                    WHERE movies_title = :e1 AND projections_date_time >= current_date""")
        rs = conn.execute(s, e1=mov)
    else:
        s = text("""SELECT movies_title, projections_date_time, projections_price, projections_id, rooms_name
                    FROM public.projections
                    JOIN public.movies ON projections_movie = movies_id
                    JOIN public.directors ON movies_director = directors_id
                    JOIN public.rooms ON projections_room = rooms_id
                    WHERE projections_date_time >= current_date
                    ORDER BY projections_date_time, movies_title, rooms_name""")
        rs = conn.execute(s)
    proj = rs.fetchall()
    conn.close()
    return proj


def how_many_seats_left(proj_id):
    conn = engine.connect()
    s = text("""SELECT COUNT(seats_id) as s
                     FROM seats
                     WHERE seats_id NOT IN (
                        SELECT seats_id
                        FROM public.projections
                        JOIN public.tickets ON tickets_projection = projections_id
                        JOIN public.seats ON tickets_seat = seats_id
                        WHERE projections_id = :e1)""")
    rs = conn.execute(s, e1=proj_id)
    f = rs.fetchone()
    return f.s


def free_seats(proj_id):
    conn = engine.connect()
    s = text("""SELECT *
                 FROM seats
                 WHERE seats_id NOT IN (
                    SELECT seats_id
                    FROM public.projections
                    JOIN public.tickets ON tickets_projection = projections_id
                    JOIN public.seats ON tickets_seat = seats_id
                    WHERE projections_id = :e1)""")
    rs = conn.execute(s, e1=proj_id)
    f = rs.fetchall()
    return f


def get_seat_by_name(room_id, seat_name):
    conn = engine.connect()
    s = text("""SELECT * FROM public.seats JOIN public.rooms ON seats.seats_room = rooms.rooms_id
                WHERE rooms_id = :e1 AND seats_name = :e2 """)
    rs = conn.execute(s, e1=room_id, e2=seat_name)
    se = rs.fetchone()
    conn.close()
    return se


def get_directors():
    conn = engine.connect()
    s = text("SELECT * FROM public.directors")
    rs = conn.execute(s)
    dire = rs.fetchall()
    conn.close()
    return dire


def get_rooms():
    conn = engine.connect()
    s = text("SELECT * FROM public.rooms")
    rs = conn.execute(s)
    dire = rs.fetchall()
    conn.close()
    return dire