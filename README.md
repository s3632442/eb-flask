# s3632442-a2-t1
to deploy just run sudo systemctl start a2-t1.service
if resources are being estabilshed for the first time you will hit a race case where the resoureces being deployed are still being created when the program tries to access them so you will have to run it again
sudo systemctl start a2-t1.service
you can see this all happen in the journal output
only thing missing is search by year