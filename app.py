from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from bokeh.plotting import figure, output_file, show

app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]="postgresql://postgres:postpass123@localhost/tallyhome"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]= False
db=SQLAlchemy(app)

class Data(db.Model):
    __tablename__ = "data"
    id=db.Column(db.Integer, primary_key=True)
    vistype_=db.Column(db.String(30))
    qsandas_=db.Column(db.ARRAY(db.String(120)))
    results_=db.Column(db.ARRAY(db.Integer))

    def __init__(self, vistype_, qsandas_, results_):
        self.vistype_=vistype_
        self.qsandas_=qsandas_
        self.results_=results_


# Pages
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/success", methods=["POST", "GET"])
def success():
    qsandas=[]
    results=[]
    #store values correctly
    if request.method=='POST':
        vistype = request.form["vistype"]
        if (vistype == "scatter"):
            #read in (X,Y){Q, axis, min, max, step}
            qsandas = [request.form["xq"],request.form["xaxis"],request.form["xmin"],
            request.form["xmax"],request.form["xstep"],request.form["yq"],
            request.form["yaxis"],request.form["ymin"],request.form["ymax"],request.form["ystep"]]
            #votes[0] will be an array of x results, votes[1] will be an array of y results
            results.append([0])
            results.append([0])
            #   you will have to ignore results[0][0] and results[1][0],
            #maybe do the above with each spot in votes being a
            #   dictionary with an x and y value?
        elif (vistype == "pie"):
            qsandas.append(request.form["question"])
            qsandas.append(request.form["numans"])
            for i in range(1, int(request.form["numans"])+1):
                qsandas.append(request.form["ans"+str(i)])
                results.append(0) #each option is given a vote spot, 0--> #options-1
        elif (vistype == "bar"):
            qsandas.append(request.form["question"])
            qsandas.append(request.form["numans"])
            for i in range(1, int(request.form["numans"])+1):
                qsandas.append(request.form["ans"+str(i)])
                results.append(0) #each option is given a vote spot, 0--> #options-1
        elif (vistype == "histo"):
            qsandas = [request.form["q"],request.form["min"],request.form["max"],
            request.form["step"],request.form["ranges"]]
            #each space in votes[] is an input, so no need to modify it
        data=Data(vistype,qsandas,results)
        db.session.add(data)
        db.session.commit()
    return render_template("success.html", id=Data.query.all()[-1].id)

@app.route('/<int:tally_id>/')
def show_tally(tally_id):
    df=Data.query.get(tally_id)
    return render_template("tally.html", id=tally_id, vistype=df.vistype_, qsandas=df.qsandas_)

@app.route('/<int:tally_id>/results', methods=["POST", "GET"])
def show_tally_results(tally_id):
    df=Data.query.get(tally_id)

    print(df.results_)
    if request.method=='POST':
        if df.vistype_ == "scatter":
            print(Data.__table__)
            print(type(df.results_))
            df.results_[0].append(request.form["x"])
            df.results_[1].append(request.form["y"])
            print(df.results_)
            print(type(df.results_))
        elif df.vistype_ == "pie":
            df.results_[int(request.form["pans"])] += 1
        elif df.vistype_ == "bar":
            df.results_[int(request.form["bans"])] += 1
        elif df.vistype_ == "histo":
            df.results_.append(request.form["histo_input"])
        #print(df.results_)
        #db.session.add(df)
    if df.vistype_ == "scatter":
        plot=figure(plot_width=500, plot_height=400, title=df.qsandas_[0])
        plot.xaxis.axis_label=df.qsandas_[1]
        plot.yaxis.axis_label=df.qsandas_[6]
        plot.circle(df.results_[0][1:], df.results_[1][1:], size=5, color="red", alpha=0.5)
        show(plot)
    print(df.results_)
    db.session.commit()
    print(df.results_)
    return render_template("tally_results.html", id=tally_id)

# Run
if __name__ == '__main__':
    app.debug=True
    app.run()
