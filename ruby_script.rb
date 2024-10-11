task_name = 'SS_3515'
csv_file = task_name + '_result.csv'

# CompanyUser.where

nins = ['1069645215', '1084911609', '1089880049']

nins.each do |nin|
  user = CompanyUser.find_by(identity_number: SakaniEncrypt.encrypt(nin))
  if user
    user.destroy
    pp 'Done'
  else
    pp 'NOT EXIST'
  end
end

