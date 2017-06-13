from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from bokeh.plotting import figure, output_file, show
from bokeh.charts import Donut, Bar, Histogram, show
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.palettes import viridis
import pandas as pd
from arraytype import MutableList
from numpy import pi

app=Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"]="postgres://lirwqhqvzsxzdb:d4ed5b2950414d1ef2fb4bc43e52c35d50324cb15ca38e01184ddfe810f79e9e@ec2-107-20-186-238.compute-1.amazonaws.com:5432/dcmi0jn734lorb?sslmode=require"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]= False
db=SQLAlchemy(app)

class Data(db.Model):
    __tablename__ = "tallies"
    id=db.Column(db.Integer, primary_key=True)
    vistype_=db.Column(db.String(30))
    qsandas_=db.Column(db.ARRAY(db.String(120)))
    results_=db.Column(MutableList.as_mutable(db.ARRAY(db.Integer)))

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
            # every even index spot in results_[] is an x value ([0],[2],[4]...)
            # every odd index spot in results_[] is a y value ([1],[3],[5]...)
        elif (vistype == "pie"):
            qsandas.append(request.form["question"])
            qsandas.append(request.form["numans"])
            for i in range(1, int(request.form["numans"])+1):
                qsandas.append(request.form["ans"+str(i)])
            # each spot in results_[] is the index of voted value
            #   (voted value = qsandas[results[0]+2])
        elif (vistype == "bar"):
            qsandas.append(request.form["question"])
            qsandas.append(request.form["numans"])
            for i in range(1, int(request.form["numans"])+1):
                qsandas.append(request.form["ans"+str(i)])
            # each spot in results_[] is the index of voted value
            #   (voted value = qsandas[results[0]+2])
        elif (vistype == "histo"):
            qsandas = [request.form["q"],request.form["label"],request.form["min"],request.form["max"],
            request.form["step"],request.form["ranges"]]
            # each spot in results_[] is the inputted value
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
    if request.method=='POST':
        if df.vistype_ == "scatter":
            df.results_.append(int(request.form["x"]))
            df.results_.append(int(request.form["y"]))
        elif df.vistype_ == "pie":
            df.results_.append(int(request.form["pans"]))
        elif df.vistype_ == "bar":
            df.results_.append(int(request.form["bans"]))
        elif df.vistype_ == "histo":
            df.results_.append(int(request.form["histo_input"]))
        db.session.commit()
    if df.vistype_ == "scatter":
        tally=figure(plot_width=500, plot_height=400, title=df.qsandas_[0], tools="")
        tally.xaxis.axis_label=df.qsandas_[1]
        tally.yaxis.axis_label=df.qsandas_[6]
        xvalues=[]
        yvalues=[]
        for i in range(0,len(df.results_),2):
            xvalues.append(df.results_[i])
            yvalues.append(df.results_[i+1])
        tally.circle(xvalues, yvalues, size=7, color="red", alpha=0.5)
    elif df.vistype_ == "pie":
        numopts = int(df.qsandas_[1])
        # Create a list of percent vote share for each option in the Tally
        percents = [df.results_.count(i)/len(df.results_) for i in range(numopts)]
        # Create a list of colours from the pallete of correct length
        colours = viridis(numopts)
        """ # Using plotting - revisit if you can erase axis lines
            # Would use this because more control over labels, etc.
        starts = [p*2*pi for p in percents[:-1]]
        ends = [p*2*pi for p in percents[1:]]

        tally = figure(x_range=(-1,1), y_range=(-1,1))
        tally.wedge(x=0, y=0, radius=1, start_angle=starts, end_angle=ends, color=colours)
        show(tally)"""
        # Create a Pandas series out of percents and answer labels
        data = pd.Series(percents,
         index=[df.qsandas_[i+2] for i in range(numopts)])
        tally = Donut(data, color=colours, hover_text="%",tools="")
    elif df.vistype_ == "bar":
        numopts = int(df.qsandas_[1])
        # Create a list of total vote count for each option in the Tally
        votecounts = [df.results_.count(i) for i in range(numopts)]
        # Create a list of colours from the pallete of correct length
        colours = viridis(numopts)
        # Create a table out of vote counts and answer labels
        data = {
            'option': df.qsandas_[2:],
            'votes': votecounts
        }
        # All one colour, but properly spaced bars:
        #   tally = Bar(data, values='votes', label='option', color=colours, plot_width=400)
        tally = Bar(data, values='votes', label='option', color=colours, group='option', plot_width=400,tools="")
    elif df.vistype_ == "histo":
        tally = Histogram(df.results_, bins=int(df.qsandas_[5]), plot_width=400,tools="")
    script1, div1 = components(tally)
    cdn_js=CDN.js_files[0]
    cdn_css=CDN.css_files[0]
    return render_template("tally_results.html", id=tally_id, title=df.qsandas_[0],
     embedscript=script1, embeddiv=div1, cdncss=cdn_css, cdnjs=cdn_js)

# Run
if __name__ == '__main__':
    app.run(debug=False)
